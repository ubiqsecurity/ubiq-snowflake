#!/bin/bash

read -p "AWS Profile Name (default: none): " aws_profile

aws_region=$(eval "aws configure get region")

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
# mkdir package
# install cryptography separately because platforms
pip3 install --target $package_dir --platform manylinux_2_12_x86_64 --implementation cp --python 3.10 --only-binary=:all: --upgrade cryptography
pip3 install --target $package_dir -r requirements.txt --platform manylinux_2_12_x86_64 --implementation cp --python 3.10 --only-binary=:all:

broker_fns=("fetch_ffs" "fetch_fpe_key" "fetch_ffs_and_fpe_key" "submit_events")

for fn in "${broker_fns[@]}"
do
    # create archive and upload function
    (cd $package_dir; zip -r ../${fn}_deploy.zip .)
    (cd fetch_ffs; zip -r ../${fn}_deploy.zip .)
    zip -r ${fn}_deploy.zip common

    # Check if function exists
    aws_fn_exist=$(eval "aws lambda get-function --function-name ${fn} ${aws_region:+"--region ${aws_region}"} ${aws_profile:+"--profile ${aws_profile}"}")
    if [ -z ${aws_fn_exist+x} ]; then
        echo "Creating function ${fn}"
        eval "aws lambda create-function --function-name ${fn} --zip-file fileb://${fn}_deploy.zip ${aws_region:+"--region ${aws_region}"} ${aws_profile:+"--profile ${aws_profile}"} --role $aws_role --runtime 'python3.10' --handler 'lambda_function.lambda_handler'"
    else
        echo "Updating function ${fn}"
        eval "aws lambda update-function-code --function-name ${fn} --zip-file fileb://${fn}_deploy.zip ${aws_region:+"--region ${aws_region}"} ${aws_profile:+"--profile ${aws_profile}"}"
    fi
done

# Clean up
echo "removing pip package folder '${package_dir}'"
rm -rf $package_dir