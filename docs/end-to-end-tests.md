## E2E environment using terraform
This folder contains tools that can be used to deploy kubernetes cluster on :
 - local VM's
 - AWS VM's (WIP)

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
    * ***NOTE 1:**  `make install` copies output binary into */usr/local/bin* directory, make sure it's in PATH envionment variable*
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
    * ***NOTE 1:** Make sure, that Ansible is using Python 2.7. A lot of Ansible scripts are prepared exlusivly for Python 2.7*
    * ***NOTE 3:** You may need to increase number of file handles. For GNU\Linux use ulitmit. MacOS X users should run `sudo launchctl limit maxfiles unlimited`*

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

* ***NOTE 1:** 
Kubectl is installed only on Kubernetes master node (usually named: *k8s-m1*) with all proper credentials.
In future releases, we will fetch all credentials and kubectl binary so user can interact with cluster remotely.


### AWS Kubernetes cluster
#### Deployment and purge
AWS requires `ssh-agent` as a private key provider. Corresponding public key should be available on AWS:
```sh
eval $(ssh-agent -s) // Merge current shell and ssh-agent session.
ssh-add *<path_to_key>* // Adds private key to the `ssh-agent`.
```

Following environmental variables are required:
  * `AWS_SECRET_ACCESS_KEY` - contains AWS secret access key.
  * `AWS_ACCESS_KEY_ID` - contains AWS access ID.
  * `TF_VAR_agent_seed` - contains non-colliding third subnet octet.

*Note: For following information about AWS access ID and secret access key read [this](http://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html#access-keys-and-secret-access-keys)*

```sh
cd ./terraform
# to deploy aws cluster
./setup_env.sh aws deploy
# to purge aws cluster
./setup_env.sh aws purge
```
#### Connecting to cluster
To get details about connectivity into provisioned cluster, run following commands:
```sh
cd ./terraform/aws_env
terraform output
```
