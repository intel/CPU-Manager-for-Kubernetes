<!--
Copyright (c) 2017 Intel Corporation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Releasing CMK
General flow is:
 - run `prepare_release.py` script
 - create PR, get review
 - "Rebase and merge" PR into master branch
 - If the repository has [Jenkins CI/CD](#jenkins-release-job) job
   - Jenkins CI/CD will build VM based on `.release/Vagrantfile`
   - Jenkins CI/CD will run `.release/make_release.py`
 - If there is no Jenkins CI/CD or you want to release in [manual](#manual-release) way:
   - spawn release VM (`vagrant up`in `.release` directory)
   - run `make_release.py` script in the VM
   
In any case, please read [below](#prepare-release-script) paragraph for more information.
If you want to release manually, please read also



## Prepare release script

---
The example commands given here assume:
  - The current version of CMK is `v0.1.0`.
  - The version you want to release is `v0.2.0`.
  - Your upstream git remote is named `origin`.

1. Make sure that:
  - You are on `master` branch.
  - Your `master` branch is up to date with remote `origin/master`.
  - There are no un-staged files.
  
1. Chose release tag value according to pattern `vX.Y.Z[-rcV]` and set is as environment variable `CMK_RELEASE_VER`:
  - `X` - single digit [0-9] (required)
  - `Y` - single digit [0-9] (required)
  - `Z` - single digit [0-9] (required)
  - `-rc` - indicates pre-release (optional)
	  - `V` - single or double digit 

	examples: `v0.2.0`, `v0.2.1`,`v0.0.2-rc2`,`v0.0.2-rc11`
 
1. Run `prepare_release.py` script from main repository directory:
```sh
CMK_RELEASE_VER=v0.2.0 .release/prepare_release.py
# or
export CMK_RELEASE_VER=v0.2.0
.release/prepare_release.py
```
You can execute `.release/prepare_release.py --help` to get more information.

1. Got to Github repository, create pull request and get review.
1. When review is done, use "**Rebase and merge**" button to make the release. **Do not change the release commit message.**

####**VERY IMPORTANT NOTE** - Read before you release
You need to use "Rebase and merge" in order to preserve latest commit message from release branch
(`cmk-release-v0.2.0`). The Jenkins CI/CD part of automation based on commit message prepared by `prepare_release.py` script will trigger creation of tag, creation of release and change log generation

Additionally, tag and release are created once PR from release branch gets onto master branch, if in the meantime someone makes some changes to master branch (i.e. new feature from other PR is merged) those changes will **not be** included into the release. 


## Make release
---

#### Jenkins release job
If Jenkins CI/CD is present and configured with the "release job" - no user intervention is needed.
"Release job" will spawn VM based on `Vagrantfile` from `.release` directory, setup all credentials inside the VM for repository and run `.release/make_release.py` script from the repository.

The script will look whether latest commit message on `master` branch matches:
`CMK release - version v0.2.0.` Upon failure - no release will be generated.

If the commit message matches above pattern, the script will:
 - generate tag and push tag to repository
 - generate change log between new tag and latest release
 - using [GithubAPI](https://developer.github.com/v3/repos/releases/) push the release to repository


#### Manual release
If there is no Jenkins CI/CD present you can manually create release.  The advantage of manual release process is that you can create releases not only from `master` branch but also from custom branches. 

Prerequisites:
1. Make latest commit on branch you want to release match pattern i.e. `CMK release - version v0.2.0-rc3.`, (`v0.2.0-rc3` will become tag value)
1. Make sure that changes you want to release are pushed to `origin` (any branch) .
1. Make sure that branch you are on ("release branch") is clean - no un-staged files.

Manual release steps
1. Run `vagrant up` in the `.release` directory
1. Once VM is up, SSH into the VM - `vagrant ssh`
1.  Setup `GITHUB_TOKEN` environment variable `export GITHUB_TOKEN=<your-token>`
1. Execute
```sh
cd /cmk
.release/make_release.py	
```

**NOTE**
Running Vagrant locally syncs your repository directory into `/cmk` using by default Vagrant provider method  The steps above assume that VirtualBox FS is used, which means that all changes to git repository done on local host are reflected inside VM and vice versa.


## Details
---

**What will `prepare_release.py` do :**
 - check whether script is run from main repository directory
 - check whether current branch is `master` and if it's "clean"
 - fetch origin
 - check whether `CMK_RELEASE_VER` is set, follows proper pattern and there in no existing tag with it's value
 - check whether there is no `cmk-release-v1.3.0` branch neither locally nor remotely
 - get previous version string from `Makefile` (`version=v1.3.0`) and check

If all above checks pass, script will:
 - create local branch `cmk-release-v1.3.0`
 - replace old release string (`v1.3.0`) with new one (`v1.3.0`) in all repo files
 - commit changes with message `CMK release - version v1.3.0.`
 - push branch to origin
 - checkout to `master` branch.

**What will happen after PR gets to `master` branch**
After PR is "Rebased and merged" into `master` branch, Jenkins CI/CD will start VM based on `.release/Vagrantfile` and execute `.release/make_release.py` inside the VM.

**What will `make_release.py` do :**
- check latest commit message for `CMK release - version v1.3.0.` string
- `v1.3.0` will become tag value
- generate change log
- create release with change log based on tag found in commit message
