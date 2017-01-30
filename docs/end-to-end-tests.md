## E2E environment using terraform
All tools which can be used to deploy kubernetes cluster are stored inside `/terraform` folder.
Currently K8s can be deployed on :
 - local VM's
 - AWS VM's

In both cases [Terraform](https://www.terraform.io/) is used as the deployment tool and [Kargo](https://github.com/kubernetes-incubator/kargo) as Kubernetes deployer. Details on the 
directories and files are as follows:
 - *aws_env/*: terraform files for AWS based environment
 - *scripts/*: helper shell scripts
 - *shared/*: helper module for shared code between local and AWS deployment used to create Kargo inventory
 - *vagrant_env/*: terraform files for local vagrant based environment
 - *aggregator/*: helper module for data aggregation
 - *variables.tf*: file with VM's configuration
 - *setup_env.sh*: Shell script to deploy and purge e2e environments

### Prerequisites:
1. [VirtualBox](https://www.virtualbox.org/wiki/VirtualBox)
1. [Vagrant](https://www.vagrantup.com/)
1. [GO](https://golang.org/)
    * setup GOPATH
    * setup GOROOT
1. [Terraform](https://www.terraform.io/)
    * Download *terraform*
    * Unpack binary *terraform*
    * Copy *terraform* binary to directory accesible from PATH env.
    ```sh
    unzip terraform_0.8.2_linux_amd64.zip
    cp terraform /usr/local/bin
    ```
1. [terraform-provider-vagrant](https://github.com/intelsdi-x/terraform-provider-vagrant)
    * Clone git repository (tag: v0.1.0) 
    * Build and install
    ```sh
    cd $GOPATH/src/github.com/intelsdi-x
    git clone -b v0.1.0 git@github.com:intelsdi-x/terraform-provider-vagrant
    cd terraform-provider-vagrant
    make build
    make install
    ```
    * **NOTE:**  `make install` copies output binary into */usr/local/bin* directory, make sure it's in PATH envionment variable
    * MacOS X users should also fulfill theirs `~/.terraformrc`:
    ```sh
    providers {
      vagrant = "/usr/local/bin/terraform-provider-vagrant"
    }
    ```

1. [Ansible](https://www.ansible.com/) (currently 2.2.0.0 version is tested, **dont use any other**)
    ```sh
    sudo pip2 install ansible==2.2.0.0
    ```script
    * **NOTE:** Make sure, that Ansible is using Python 2.7. A lot of Ansible scripts are prepared exlusivly for Python 2.7*
    * **NOTE:** You may need to increase number of file handles. For GNU\Linux use ulitmit. MacOS X users should run `sudo launchctl limit maxfiles unlimited`*

1. [gnu-sed](https://www.gnu.org/software/sed/manual/sed.html) (MacOS X only)
    ```sh
    brew install gnu-sed
    ```

### Local Kubernetes cluster
#### Deployment and purge

```sh
cd ./terraform
# to deploy local cluster 
./setup_env.sh vagrant deploy
# to purge local cluster
./setup_env.sh vagrant purge
```


#### Connecting to cluster

After provisioning is completed, file located in *./terraform/workdir/mvp_inventory/ansible_inventory* contains details
about provisoned VM's: 
 - `ansible_ssh_host`  VM's IP, for local VM's its 127.0.0.1
 - `ansible_ssh_port`  SSH port
 - `ansible_ssh_user`  VM's user name
 - `ansible_ssh_private_key_file` - path to private key used do establish ssh connection

In order to establish SSH connection to VM, use command below:
``` sh
ssh -o StrictHostKeyChecking=no -p <ansible_ssh_port> -i <ansible_ssh_private_key_file> <ansible_ssh_user>@<ansible_ssh_host>
```

Alternatively, you can go to vagrant base directory of `ansible_ssh_private_key_file` (i.e. */tmp/vagrant_vbox_resXXXXXXXX*)
and inside there execute `vagrant ssh`.

* **NOTE 1:**
Kubectl is installed only on Kubernetes master node (usually named: *k8s-m1*) with all proper credentials.
In future releases, we will fetch all credentials and kubectl binary so user can interact with cluster remotely.


### AWS Kubernetes cluster
#### Deployment and purge
To provide connectivity into VMs, AWS is using user's public keys. To learn more about AWS key management(incl. how to add another key) read [this](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html).
For e2e environment purposes, public key is defined within `terraform/aws_env/env_variables.tf` as `aws_keyname` variable. User can change this directly
inside this file, or override it with `TF_VAR_aws_keyname`.

To provide connectivity from your device, terraform requires `ssh-agent` as a private key provider:
```sh
# Merge current shell and ssh-agent session.
eval $(ssh-agent -s)
# Adds private key to the `ssh-agent`.
ssh-add <path_to_key>
```

Following environment variables are required:
  * `AWS_SECRET_ACCESS_KEY` - contains AWS secret access key.
  * `AWS_ACCESS_KEY_ID` - contains AWS access ID.
  * `TF_VAR_agent_seed` - contains the fird octed of a 32 bit subnet mask in decimal. Used to make unique private subnets inside single VPC. For more information read [networking](#networking)

*Note: For following information about AWS access ID and secret access key read [this](http://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html#access-keys-and-secret-access-keys)*


```sh
cd ./terraform
# to deploy aws cluster
setup_env.sh aws deploy
# to purge aws cluster
setup_env.sh aws purge
```

#### Networking
AWS is delivering private networking with [VPC](https://aws.amazon.com/vpc/). E2E envionment is expecting terraform's `*.tfstate` file with generated VPC exported to S3.
To point to custom `*.tfstate` file you need to export following envionmental variables:
  * `TF_VAR_tf_bucket_name` - S3 bucket name, where `*.tfstate` file is located.
  * `TF_VAR_vpc_state_file` - `*.tfstate` file location.

VPC is delivering pool of IP addresses. This pool is splited into smaller subnets during environment spawning. To provide non-colliding subnets, for each
envionment, use unique `TF_VAR_agent_seed` for each deployment. `TF_VAR_agent_seed` must be integer choosen from range <0-255> in other case whole deployment
will fail.

#### Connecting to cluster
To get details about connectivity into provisioned cluster, run following commands:
```sh
cd ./terraform/aws_env
terraform output
```
