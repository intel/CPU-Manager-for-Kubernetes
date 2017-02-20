# Releasing KCM

The example commands given here assume:
- The current version of KCM is `v3.2.1`.
- The version you want to release is `v0.3.0-rc1`.
- Your upstream git remote is named `origin`.

1. Create a local release branch.
   ```
   git checkout master
   git pull origin master
   git checkout -b release-v0.3.0-rc1
   ```

1. Update the version string in the entire repository.
   ```
   git ls-files | xargs -I {} sed -i "" "s/v0\.2\.0/v0.3.0-rc1/g" {}
   ```

1. Commit changes.
   ```
   git add -u
   git commit -m "Bumped version to v0.3.0-rc1."
   ```

1. Build HTML docs.
   ```
   make docs
   ```

1. Commit changes.
   ```
   git add -u
   git commit -m "Regenerated HTML docs."
   ```

1. Push branch and create a PR.
   ```
   git push origin release-v0.3.0-rc1
   ```

1. Get review, wait for CI to pass, merge the release branch to upstream master.

1. Update local master branch.
   ```
   git checkout master
   git pull origin master
   ```

1. Create a git tag and push it upstream.
   ```
   git tag -a v0.3.0-rc1 -m "KCM v0.3.0-rc1"
   git push origin --tags
   ```

1. Manually test the tarball.
   Download https://github.com/intelsdi-x/kubernetes-comms-mvp/archive/v0.3.0-rc1.tar.gz

   ```
   tar -xf v0.3.0-rc1.tar.gz
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
