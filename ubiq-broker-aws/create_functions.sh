#!/bin/bash

read -p "AWS Profile Name (default: default): " aws_profile
aws_profile=${aws_profile:-default}

aws_region=$(eval "aws configure get region")
aws_profile=${aws_profile:-"us-west-2"}

read -p "Lambda Execution Role? (arn:aws:iam...) " aws_role

# Grab python pacakages to be included in the archive
package_dir="package"
if [ -d $package_dir ] 
then
    while [ -d $package_dir ]
    do
        echo "'${package_dir}' directory exists."
        read -p "Alternate (new) folder name for storing pip packages? " package_dir 
    done
    mkdir $package_dir
else
    echo "Creating pip package directory"
    mkdir $package_dir
fi
sleep 1
echo "folder created"

# install cryptography separately because platforms
pip install --target $package_dir --platform manylinux_2_12_x86_64 --implementation cp --python 3.10 --only-binary=:all: --upgrade cryptography
pip install --target $package_dir -r requirements.txt --platform manylinux_2_12_x86_64 --implementation cp --python 3.10 --only-binary=:all:

broker_fns=("fetch_dataset_and_structured_key" "submit_events")

for fn in "${broker_fns[@]}"
do
    # create archive and upload function
    (cd $package_dir; zip -r ../${fn}_deploy.zip .)
    (cd $fn; zip -r ../${fn}_deploy.zip .)
    zip -r ${fn}_deploy.zip common

    # Check if function exists
    aws lambda get-function --function-name $fn --region $aws_region --profile $aws_profile > /dev/null 2>&1
    if [ 0 -eq $? ]; then
        echo $?
        echo "Updating function ${fn}"
        aws lambda update-function-code --function-name $fn --zip-file fileb://$fn_deploy.zip --region $aws_region --profile $aws_profile
    else
        echo $?
        if [ -z "$aws_role" ]; then
            echo "Lambda execution role is required for creating lambda functions"
            exit 1
        else 
            echo "Creating function ${fn}"
            aws lambda create-function --function-name $fn --zip-file fileb://$fn_deploy.zip --region $aws_region --profile $aws_profile --role $aws_role --runtime 'python3.10' --handler 'lambda_function.lambda_handler'
        fi
    fi
done

# Clean up
echo "removing pip package folder '${package_dir}'"
rm -rf $package_dir