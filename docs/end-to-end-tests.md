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
    * Clone git repository
    * Build and install
    ```sh
    cd $GOPATH/src/github.com/intelsdi-x
    git clone git@github.com:intelsdi-x/terraform-provider-vagrant
    cd terraform-provider-vagrant
    make build
    make install
    ```
    ***NOTE:**  `make install` copies output binary into */usr/local/bin* directory, make sure it's in PATH envionment variable*
    * MacOS X users should also fulfill theirs `~/.terraformrc`:
    ```json
    providers {
      vagrant = "/usr/local/bin/terraform-provider-vagrant"
    }
    ```

1. [Ansible](https://www.ansible.com/) (currently 2.2.0.0 version is tested)
    ```sh
    sudo pip2 install ansible==2.2.0.0
    ```
    * ***NOTE 1:** Make sure, that Ansible is using Python 2.7. A lot of Ansible scripts are prepared exlusivly for Python 2.7*
    * ***NOTE 2:** Kargo isn't supporting Ansible 2.2.1.0 and newer*
    * ***NOTE 3:** You may need to increase number of file handles. For GNU\Linux use ulitmit. MacOS X users should run `sudo launchctl limit maxfiles unlimited`*

1. [gnu-sed](https://www.gnu.org/software/sed/manual/sed.html) (MacOS X only)
    ```sh
    brew install gnu-sed
    ```

### Deploying and purging local Kubernetes cluster

```sh
cd ./terraform
# to deploy local cluster 
./setup_env.sh deploy
# to purge local cluster
./setup_env.sh purge
```

### Deploying and purging AWS Kubernetes cluster
TBD
