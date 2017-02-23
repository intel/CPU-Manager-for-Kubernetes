# Releasing KCM
General flow is:
 - run `prepare_release.py` script
 - create PR, get review
 - "Rebase and merge" PR into master branch
 - Jenkins CI/CD will build VM based on `.release/Vagrantfile`
 - Jenkins CI/CD will run `.release/make_release.py`

### Short Version
---

The example commands given here assume:
  - The current version of KCM is `v0.3.0-rc1`.
  - The version you want to release is `v0.3.0-rc1`.
  - Your upstream git remote is named `origin`.

1. Make sure that:
  - You are on `master` branch.
  - Your `master` branch is up to date with remote `origin/master`.
  - There are no un-staged files.
  
1. Chose release tag value according to pattern `vX.Y.Z[-rcV]` and set is as environment variable `KCM_RELEASE_VER`:
  - `X` - single digit [0-9] (required)
  - `Y` - single digit [0-9] (required)
  - `Z` - single digit [0-9] (required)
  - `-rc` - indicates pre-release (optional)
	  - `V` - single or double digit 

	examples: `v0.3.0-rc1`, `v0.1.3`.
 
1. Run `prepare_release.py` script from main repository directory:
```sh
KCM_RELEASE_VER=v0.3.0-rc1 .release/prepare_release.py
# or
export KCM_RELEASE_VER=v0.3.0-rc1 
.release/prepare_release.py
```
You can execute `.release/prepare_release.py --help` to get more information.

1. Got to Github repository, create pull request and get review.
1. When review is done, use "**Rebase and merge**" button to make the release. Do not change the release commit message.

####**VERY IMPORTANT NOTE** - Read before you release
You need to use "Rebase and merge" in order to preserve latest commit message from release branch
(`kcm-release-v0.3.0-rc1`). The Jenkins CI/CD part of automation based on commit message prepared by `prepare_release.py` script will trigger creation of tag, creation of release and change log generation

Additionally, tag and release are created once PR from release branch gets onto master branch, if in the meantime someone makes some changes to master branch (i.e. new feature from other PR is merged) those changes will be included into the release. Make sure that 


### Details
---

**What will `prepare_release.py` do :**
 - check whether script is run from main repository directory
 - check whether current branch is `master` and if it's "clean"
 - fetch origin
 - check whether `KCM_RELEASE_VER` is set, follows proper pattern and there in no existing tag with it's value
 - check whether there is no `kcm-release-v0.3.0-rc1` branch neither locally nor remotely
 - get previous version string from `Makefile` (`version=v0.3.0-rc1`) and check

If all above checks pass, script will:
 - create local branch `kcm-release-v0.3.0-rc1`
 - replace old release string (`v0.3.0-rc1`) with new one (`v0.3.0-rc1`) in all repo files
 - commit changes with message `KCM release - version v0.3.0-rc1.`
 - push branch to origin
 - checkout to `master` branch.

**What will happen after PR gets to `master` branch**
After PR is "Rebased and merged" into `master` branch, Jenkins CI/CD will start VM based on `.release/Vagrantfile` and execute `.release/make_release.py` inside the VM.

**What will `make_release.py` do :**
- check latest commit message for `KCM release - version v0.3.0-rc1.` string
- generate change log
- create release with change log based on tag found in commit message
