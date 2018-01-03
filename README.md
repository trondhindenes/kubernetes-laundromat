# Kubernetes-Laundromat

Laundromat is a continously running container that will look for and delete old pods in your Kubernetes cluster.

You can control Laundromat by settings the following environment variables:

`DRY_RUN`: set to 'false' to allow Laundromat to actually delete pods. If not it will simply dry-run   
`MINIMUM_POD_COUNT`: Only delete pod in deployments running this number of pods or higher.    
`MINIMUM_POD_AGE_MINUTES`: Only delete pod with this age (in minutes) or older.   
`IGNORE_NAMESPACES`: Comma-separated list of namespaces to ignore. You can use wildcards, such as `*system, monitoring`.   
`IGNORE_DEPLOYMENT_NAMES`: Comma-separated list of deployment names to ignore. You can use wildcards, such as `*redis*, *db*`.   
`MAX_OP_PER_DEPLOYMENT`: Max number of operations per deployment per loop. Defaults to one. Increase if you have large number of pods.   
`LOOP_SLEEP_MINUTES`: Sleep this long inbetween runs. Defaults to 60.   