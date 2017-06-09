kon delete clusterrole CMK-third-party-resource-controller
kon delete clusterrolebinding csa-binding
kon delete clusterrolebinding csa-binding2
kon delete serviceaccount cmk-sa
kon create -f ./crole.yaml
kon create -f ./csa.yaml
kon create -f ./cbind.yaml
kon create -f ./cbind2.yaml
