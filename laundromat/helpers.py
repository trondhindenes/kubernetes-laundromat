import datetime
import fnmatch
import logging
import math
import pytz


class LaundromatHelpers():
    @staticmethod
    def dict_to_string(input_obj):
        out= ''
        for item in input_obj.keys():
            substring = '{}={}'.format(item, input_obj[item])
            out = out + substring + ','
        return out[:-1]

    @staticmethod
    def get_rs_from_deployment(deployment, extensions_client):
        deployment_selector = deployment.spec.selector.match_labels
        deployment_selector_string = LaundromatHelpers.dict_to_string(deployment_selector)
        deployment_namespace = deployment.metadata.namespace

        replica_sets = extensions_client.list_namespaced_replica_set(namespace=deployment_namespace,
                                                                     label_selector=deployment_selector_string)
        if len(replica_sets.items) == 0:
            pass
        elif len(replica_sets.items) == 1:
            this_rs = replica_sets.items[0]
        else:
            this_rs = \
                sorted(replica_sets.items, key=lambda x: int(x.metadata.annotations['deployment.kubernetes.io/revision']),
                       reverse=True)[0]
        #print('   {}'.format(this_rs.metadata.name))
        if this_rs:
            return this_rs

        return None

    @staticmethod
    def get_pods_from_replica_set(replica_set, core_client):
        rs_selector = replica_set.spec.selector.match_labels
        rs_selector_string = LaundromatHelpers.dict_to_string(rs_selector)
        rs_namespace = replica_set.metadata.namespace
        pods = core_client.list_namespaced_pod(namespace=rs_namespace, label_selector=rs_selector_string)

        return pods

    @staticmethod
    def get_pod_age(pod):
        utc_now = datetime.datetime.utcnow()
        utc_now = utc_now.replace(tzinfo=pytz.utc)

        pod_created_timestamp = pod.metadata.creation_timestamp
        pod_age = utc_now - pod_created_timestamp
        pod_age_minutes = math.ceil(pod_age.seconds/60)
        return pod_age_minutes

    @staticmethod
    def delete_pod(pod, core_client, dry_run=True):

        if dry_run:
            logging.warning('deleting pod {} (dry run)'.format(pod.metadata.name))
        else:
            logging.warning('deleting pod {}'.format(pod.metadata.name))
            core_client.delete_namespaced_pod(name=pod.metadata.name, namespace=pod.metadata.namespace, body={})

    @staticmethod
    def match_deployment_name(deployment_name, ignore_deployment_names):
        match_names = ignore_deployment_names.split(',')
        has_match = False
        for name in match_names:
            result = fnmatch.fnmatch(deployment_name, name)
            if result:
                has_match = True

        return has_match

    @staticmethod
    def match_namespace_name(namespace, ignore_namespaces):
        match_namespaces = ignore_namespaces.split(',')
        has_match = False
        for namespace_filter in match_namespaces:
            result = fnmatch.fnmatch(namespace, namespace_filter)
            if result:
                has_match = True
        return has_match

    @staticmethod
    def str2bool(v):
        return v.lower() in ("yes", "true", "t", "1")

