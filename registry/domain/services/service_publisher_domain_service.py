import web3
from registry.domain.factory.service_factory import ServiceFactory
from registry.constants import ServiceStatus, TEST_REG_ADDR_PATH, TEST_REG_CNTRCT_PATH, EnvironmentType
from registry.exceptions import ServiceProtoNotFoundException, OrganizationNotFoundException
from common.utils import hash_to_bytesuri, json_to_file
from common import utils
from registry.config import ASSET_DIR, METADATA_FILE_PATH, ORG_ID_FOR_TESTING_AI_SERVICE, IPFS_URL, NETWORK_ID, \
    NETWORKS, BLOCKCHAIN_TEST_ENV
from common.ipfs_util import IPFSUtil
from common.blockchain_util import BlockChainUtil
from common.logger import get_logger

service_factory = ServiceFactory()
ipfs_client = IPFSUtil(IPFS_URL['url'], IPFS_URL['port'])
blockchain_util = BlockChainUtil(provider=NETWORKS[NETWORK_ID]["http_provider"], provider_type="HTTP_PROVIDER")
logger = get_logger(__name__)
METADATA_URI_PREFIX = "ipfs://"


class ServicePublisherDomainService:
    def __init__(self, username, org_uuid, service_uuid):
        self._username = username
        self._org_uuid = org_uuid
        self._service_uuid = service_uuid

    @staticmethod
    def publish_service_proto_to_ipfs(service):
        proto_url = service.assets.get("proto_files", {}).get("url", None)
        if proto_url is None:
            raise ServiceProtoNotFoundException
        proto_ipfs_hash = utils.publish_zip_file_in_ipfs(file_url=proto_url,
                                                   file_dir=f"{ASSET_DIR}/{service.org_uuid}/{service.uuid}",
                                                   ipfs_client=ipfs_client)
        service.proto = {
            "model_ipfs_hash": proto_ipfs_hash,
            "encoding": "proto",
            "service_type": "grpc"
        }
        service.assets["proto_files"]["ipfs_hash"] = proto_ipfs_hash
        return service

    @staticmethod
    def publish_service_metadata_to_ipfs(service):
        service_metadata = service.to_metadata()
        if not service.is_metadata_valid(service_metadata):
            logger.info("Service metadata is not valid")
            raise Exception("INVALID_METADATA")
        filename = f"{METADATA_FILE_PATH}/{service.uuid}_service_metadata.json"
        json_to_file(service_metadata, filename)
        metadata_ipfs_hash = ipfs_client.write_file_in_ipfs(filename, wrap_with_directory=False)
        service.metadata_uri = METADATA_URI_PREFIX + metadata_ipfs_hash
        return service

    @staticmethod
    def organization_exist_in_blockchain(org_id):
        # get list of organization from blockchain
        return True
        orgs = []
        if org_id in orgs:
            return True
        return False

    @staticmethod
    def service_exist_in_blockchain(org_id, service_id):
        # get list of services
        services = []
        if service_id in services:
            return True
        return True

    def generate_blockchain_transaction_for_test_environment(*positional_inputs, method_name):
        transaction_object = blockchain_util.create_transaction_object(*positional_inputs, method_name=method_name,
                                                                       address=BLOCKCHAIN_TEST_ENV["executor_address"],
                                                                       contract_path=TEST_REG_CNTRCT_PATH,
                                                                       contract_address_path=TEST_REG_ADDR_PATH,
                                                                       net_id=BLOCKCHAIN_TEST_ENV["network_id"])
        return transaction_object

    @staticmethod
    def update_service_in_blockchain(org_id, service_id, metadata_uri, environment):
        method_name = "updateServiceRegistration"
        positional_inputs = (web3.Web3.toHex(text=org_id), web3.Web3.toHex(text=service_id), metadata_uri)
        if environment == EnvironmentType.TEST.value:
            executor_key = BLOCKCHAIN_TEST_ENV["executor_key"]
            transaction_object = ServicePublisherDomainService.generate_blockchain_transaction_for_test_environment(
                *positional_inputs, method_name=method_name)
        else:
            logger.info("Environment Not Found.")
        raw_transaction = blockchain_util.sign_transaction_with_private_key(transaction_object=transaction_object,
                                                                            private_key=executor_key)
        transaction_hash = blockchain_util.process_raw_transaction(raw_transaction=raw_transaction)
        logger.info(
            f"transaction hash {transaction_hash} generated while updating service {service_id} in test blockchain "
            f"environment.")
        return transaction_hash

    @staticmethod
    def register_service_in_blockchain(org_id, service_id, metadata_uri, tags, environment):
        method_name = "createServiceRegistration"
        positional_inputs = (web3.Web3.toHex(text=org_id),
                             web3.Web3.toHex(text=service_id),
                             metadata_uri, [web3.Web3.toHex(text=tag) for tag in tags])
        if environment == EnvironmentType.TEST.value:
            executor_key = BLOCKCHAIN_TEST_ENV["executor_key"]
            transaction_object = ServicePublisherDomainService.generate_blockchain_transaction_for_test_environment(
                *positional_inputs, method_name=method_name)
        else:
            logger.info("Environment Not Found.")
        raw_transaction = blockchain_util.sign_transaction_with_private_key(transaction_object=transaction_object,
                                                                            private_key=executor_key)
        transaction_hash = blockchain_util.process_raw_transaction(raw_transaction=raw_transaction)
        logger.info(
            f"transaction hash {transaction_hash} generated while registering service {service_id} in test blockchain "
            f"environment.")
        return transaction_hash

    @staticmethod
    def register_or_update_service_in_blockchain(org_id, service_id, metadata_uri, tags, environment):
        if not ServicePublisherDomainService.organization_exist_in_blockchain(org_id=org_id):
            raise OrganizationNotFoundException()
        if ServicePublisherDomainService.service_exist_in_blockchain(org_id=org_id, service_id=service_id):
            # service exists in blockchain. update service in blockchain
            transaction_hash = ServicePublisherDomainService.update_service_in_blockchain(
                org_id=org_id, service_id=service_id, metadata_uri=metadata_uri, environment=environment)
        else:
            # service does not exists in blockchain. register service in blockchain
            transaction_hash = ServicePublisherDomainService.register_service_in_blockchain(
                org_id=org_id, service_id=service_id, metadata_uri=metadata_uri, tags=tags, environment=environment)
        return transaction_hash

    def validate_service_metadata(self):
        pass

    def publish_service_data_to_ipfs(self, service, environment):
        # publish assets
        service = self.publish_service_proto_to_ipfs(service)
        if environment == EnvironmentType.TEST.value:
            for group in service.groups:
                group.endpoints = group.test_endpoints
        service = self.publish_service_metadata_to_ipfs(service)
        return service

    def publish_service_on_blockchain(self, service, environment):
        # deploy service on testing blockchain environment for verification
        transaction_hash = self.register_or_update_service_in_blockchain(
            org_id=ORG_ID_FOR_TESTING_AI_SERVICE, service_id=service.service_id,
            metadata_uri=hash_to_bytesuri(service.metadata_uri), tags=service.tags, environment=environment)
        return service.to_dict()
