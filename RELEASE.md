# Releasing KCM

The example commands given here assume:
- The version you want to release is `v0.3.0-rc1`.
- The current version of KCM is `v0.2.0`.
- Your upstream git remote is named `origin`.

1. Make sure that you current branch is clean and up-to-date with `origin/master`,
   preferably use `master` branch.
    ```sh
    git checkout master
    git pull origin master
    git status
    ```
   
1. Setup environment variable KCM_RELEASE_VER to `v0.3.0-rc1` and run `prepare_release.sh` script from main repo directory.
    ```sh
    export KCM_RELEASE_VER=v0.3.0-rc1
    .release/prepare_release.sh
    # optionally
    KCM_RELEASE_VER=v0.3.0-rc1 .release/prepare_release.sh 
    ```

1. Script will perform the following steps:
    - Validate if `KCM_RELEASE_VER` follows pattern `vX.Y.Z[-rcV]`, where:
        - `X`,`Y`,`Z`  number between 0 and 9          (required)"
        - `-rc`    release candidate indicator     (optional)"
        - `V`      number between 0 and 99         (required only when `-rc` is present)"
    - Create a local release branch named `kcm-release-v0.3.0-rc1`
    - Find latest tag - `v0.2.0`
    - Replace `v0.2.0` tag with `KCM_RELEASE_VER` in all code in repository
    - Commit changes with message `Bumped version to v0.3.0-rc1.`
    - Rebuild all docs
    - Commit changes with message `Regenerated HTML docs for v0.3.0-rc1`
    - Push branch to `origin/kcm-release-v0.3.0-rc1`
    - Checkout to "starting" local branch

    **Note:** 
    - If local branch with name `kcm-release-v0.3.0-rc1` exists script will exit fail and won't perform any of the steps above
    - If remote branch with name `origin/kcm-release-v0.3.0-rc1` exists script will fail and won't perform any of the steps above
    - If value of `KCM_RELEASE_VER` does not meet requirements above script will fail and won't perform any of the steps above
    - Tf tag `KCM_RELEASE_VER` exists script will fail and won't perform any of the steps above



1. Create PR from `origin/kcm-release-v0.3.0-rc1`, get review, wait for CI to pass, merge the release branch to upstream master.

1. Update local master branch.
   ```
   git checkout master
   git pull origin master
   ```

1. Create a git tag and push it upstream.
   ```
   git tag -a $KCM_RELEASE_VER -m "KCM $KCM_RELEASE_VER"
   git push origin --tags
   ```

1. Manually test the tarball.
   Download https://github.com/intelsdi-x/kubernetes-comms-mvp/archive/v0.3.0-rc1.tar.gz

   ```
   tar -xf $KCM_RELEASE_VER.tar.gz
   cd <extracted-dir>
   make
   ```

1. Mark the release as a final or pre-release in GitHub, as appropriate.
   See https://github.com/intelsdi-x/kubernetes-comms-mvp/releases

1. Add release notes to the tag in GitHub, using recent releases as an
   example. Be sure to include any incompatible changes or other major
   behavior changes. Also outline bugs that were fixed since the previous
   release.

1. Attach the tarball from the GitHub releases page to an announcement email to the appropriate lists.
