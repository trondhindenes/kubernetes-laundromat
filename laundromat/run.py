import logging
import os
import time
import requests
from kubernetes import client

from laundromat.helpers import LaundromatHelpers


def main(do_dry_run=True, minimum_pod_count=3, minimum_pod_age_minutes=3600,
         ignore_namespaces='kube-system, monitoring', max_op_per_deployment=1, ignore_deployment_names=''):
    client.configuration.host = "localhost:8001"
    core_client = client.CoreV1Api()
    extensions_client = client.ExtensionsV1beta1Api()

    all_deployments = extensions_client.list_deployment_for_all_namespaces()

    for deployment in all_deployments.items:
        deployment_name = deployment.metadata.name
        deployment_has_correct_scale = False
        deployment_has_performed_op_count = 0

        logging.info('')
        logging.info('Deployment: {}'.format(deployment.metadata.name))
        deployment_replica_count = deployment.spec.replicas

        this_rs = LaundromatHelpers.get_rs_from_deployment(deployment, extensions_client)
        logging.info('ReplicaSet:     {}'.format(this_rs.metadata.name))

        deployment_pod_objects = []
        if this_rs:
            pods = LaundromatHelpers.get_pods_from_replica_set(this_rs, core_client)
            pod_items = len(pods.items)
            if deployment_replica_count == pod_items:
                deployment_has_correct_scale = True

            for pod in pods.items:

                pod_is_running = False
                if pod.status.phase == 'Running':
                    pod_is_running = True
                pod_age_minutes = LaundromatHelpers.get_pod_age(pod)
                pod_obj = {
                    "obj": pod,
                    "pod_name": pod.metadata.name,
                    "pod_age_minutes": pod_age_minutes,
                    "pod_is_running": pod_is_running
                }
                deployment_pod_objects.append(pod_obj)

                logging.info('Pod:            {}'.format(pod.metadata.name))
                logging.info('   Age (mins):  {}'.format(str(pod_age_minutes)))
                logging.info('   Running:     {}'.format(str(pod_is_running)))

        do_recycle_pod = True
        deployment_recycle_operation_count = 0
        pod_count = len(deployment_pod_objects)

        logging.info('')
        logging.info('')
        # sort so we delete the oldest pod first
        deployment_pod_objects = sorted(deployment_pod_objects, key=lambda x: x['pod_age_minutes'], reverse=True)
        for pod in deployment_pod_objects:
            pod_name = pod['pod_name']
            logging.info('Considering pod {} for recyling'.format(pod_name))
            # Only recycle if max operations per deployment has not been exceeded
            if deployment_recycle_operation_count >= max_op_per_deployment:
                logging.info(
                    'Not recyling pod because: Deployment name {} already has maxed out operations per deployment per cycle ({})'
                        .format(
                        deployment.metadata.name,
                        str(max_op_per_deployment)))
                do_recycle_pod = False

            # Only recycle if all pods in deployment are running
            if len([x for x in deployment_pod_objects if x['pod_is_running'] is False]) > 0:
                do_recycle_pod = False

            # Only recycle if minimum pod count is present
            if pod_count <= minimum_pod_count:
                logging.info(
                    'Not recyling pod because: Deployment name {} had too few pods ({}) to be considered'.format(
                        deployment.metadata.name,
                        str(pod_count)))
                do_recycle_pod = False

            # Only recycle pod if deployment doesn't match any wildcard in ignore_deployment_names
            if LaundromatHelpers.match_deployment_name(deployment.metadata.name, ignore_deployment_names):
                logging.info(
                    'Not recyling pod because: Deployment name {} matched one of {}'.format(deployment.metadata.name,
                                                                                            ignore_deployment_names))
                do_recycle_pod = False

            if LaundromatHelpers.match_namespace_name(deployment.metadata.namespace, ignore_namespaces):
                logging.info('Not recyling pod because: Deployment namespace {} matched one of {}'.format(
                    deployment.metadata.namespace, ignore_namespaces))
                do_recycle_pod = False

            if pod_age_minutes < minimum_pod_age_minutes:
                logging.info(
                    'not recycling pod because: Pod {} is not older than minimum pod age ({})'
                        .format(pod_name, minimum_pod_age_minutes))
                do_recycle_pod = False

            if do_recycle_pod:
                deployment_recycle_operation_count += 1
                pod_count -= 1
                LaundromatHelpers.delete_pod(pod['obj'], core_client, dry_run=do_dry_run)
            logging.info('')

def loop():
    dry_run_str = os.getenv('DRY_RUN', 'true').lower()
    dry_run = LaundromatHelpers.str2bool(dry_run_str)

    min_pod_count = int(os.getenv('MINIMUM_POD_COUNT', '3'))
    minimum_pod_age_minutes = int(os.getenv('MINIMUM_POD_AGE_MINUTES', '3600'))
    ignore_namespaces = os.getenv('IGNORE_NAMESPACES', 'kube-system, monitoring')
    ignore_deployment_names = os.getenv('IGNORE_DEPLOYMENT_NAMES', '')
    max_op_per_deployment = int(os.getenv('MAX_OP_PER_DEPLOYMENT', '1'))
    loop_sleep_minutes = int(os.getenv('LOOP_SLEEP_MINUTES', '60'))
    log_level = os.getenv('LOGLEVEL', 'INFO')
    if log_level.lower() == 'info':
        logging.basicConfig(level=logging.INFO)
    elif log_level.lower() == 'warning':
        logging.basicConfig(level=logging.WARNING)

    while True:
        logging.info('running laundromat with settings:')
        logging.info('DRY_RUN: {}'.format(str(dry_run)))
        logging.info('MINIMUM_POD_COUNT: {}'.format(min_pod_count))
        logging.info('MINIMUM_POD_AGE_MINUTES: {}'.format(str(minimum_pod_age_minutes)))
        logging.info('IGNORE_NAMESPACES: {}'.format(ignore_namespaces))
        logging.info('IGNORE_DEPLOYMENT_NAMES: {}'.format(ignore_deployment_names))
        logging.info('MAX_OP_PER_DEPLOYMENT: {}'.format(str(max_op_per_deployment)))
        logging.info('LOOP_SLEEP_MINUTES: {}'.format(str(loop_sleep_minutes)))

        if dry_run is False:
            logging.warning('DRY_RUN is OFF, this means that pods will potentially get deleted!!')

        api_is_ok = False
        test_url = 'http://localhost:8001/api'
        counter = 0
        while api_is_ok is False:
            if counter > 40:
                err_msg = 'unable to contact kubernetes api at url {}'.format(test_url)
                logging.error(err_msg)
                raise Exception(err_msg)
            try:
                test_reg = requests.get(test_url)
                test_reg.raise_for_status()
                api_is_ok = True
                logging.info('got in touch with Kubernetes. Iz ok.')
            except:
                pass
            counter = counter + 1
            time.sleep(0.5)

        main(dry_run, min_pod_count, minimum_pod_age_minutes, ignore_namespaces, max_op_per_deployment,
             ignore_deployment_names)
        logging.info('sleeping for {} minutes'.format(str(loop_sleep_minutes)))
        time.sleep(60 * loop_sleep_minutes)


if __name__ == '__main__':
    loop()