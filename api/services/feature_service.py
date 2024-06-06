from flask import current_app
from pydantic import BaseModel

from services.billing_service import BillingService
from services.enterprise.enterprise_service import EnterpriseService


class SubscriptionModel(BaseModel):
    plan: str = 'sandbox'
    interval: str = ''


class BillingModel(BaseModel):
    enabled: bool = False
    subscription: SubscriptionModel = SubscriptionModel()


class LimitationModel(BaseModel):
    size: int = 0
    limit: int = 0


class FeatureModel(BaseModel):
    billing: BillingModel = BillingModel()
    members: LimitationModel = LimitationModel(size=0, limit=1)
    apps: LimitationModel = LimitationModel(size=0, limit=10)
    vector_space: LimitationModel = LimitationModel(size=0, limit=5)
    annotation_quota_limit: LimitationModel = LimitationModel(size=0, limit=10)
    documents_upload_quota: LimitationModel = LimitationModel(size=0, limit=50)
    docs_processing: str = 'standard'
    can_replace_logo: bool = False


class SystemFeatureModel(BaseModel):
    sso_enforced_for_signin: bool = False
    sso_enforced_for_signin_protocol: str = ''
    sso_enforced_for_web: bool = False
    sso_enforced_for_web_protocol: str = ''


class FeatureService:

    @classmethod
    def get_features(cls, tenant_id: str) -> FeatureModel:
        features = FeatureModel()

        cls._fulfill_params_from_env(features)

        if current_app.config['BILLING_ENABLED']:
            cls._fulfill_params_from_billing_api(features, tenant_id)

        return features

    @classmethod
    def get_system_features(cls) -> SystemFeatureModel:
        system_features = SystemFeatureModel()

        if current_app.config['ENTERPRISE_ENABLED']:
            cls._fulfill_params_from_enterprise(system_features)

        return system_features

    @classmethod
    def _fulfill_params_from_env(cls, features: FeatureModel):
        features.can_replace_logo = current_app.config['CAN_REPLACE_LOGO']

    @classmethod
    def _fulfill_params_from_billing_api(cls, features: FeatureModel, tenant_id: str):
        billing_info = BillingService.get_info(tenant_id)

        features.billing.enabled = billing_info['enabled']
        features.billing.subscription.plan = billing_info['subscription']['plan']
        features.billing.subscription.interval = billing_info['subscription']['interval']

        features.members.size = billing_info['members']['size']
        features.members.limit = billing_info['members']['limit']

        features.apps.size = billing_info['apps']['size']
        features.apps.limit = billing_info['apps']['limit']

        features.vector_space.size = billing_info['vector_space']['size']
        features.vector_space.limit = billing_info['vector_space']['limit']

        features.documents_upload_quota.size = billing_info['documents_upload_quota']['size']
        features.documents_upload_quota.limit = billing_info['documents_upload_quota']['limit']

        features.annotation_quota_limit.size = billing_info['annotation_quota_limit']['size']
        features.annotation_quota_limit.limit = billing_info['annotation_quota_limit']['limit']

        features.docs_processing = billing_info['docs_processing']
        features.can_replace_logo = billing_info['can_replace_logo']

    @classmethod
    def _fulfill_params_from_enterprise(cls, features):
        enterprise_info = EnterpriseService.get_info()

        features.sso_enforced_for_signin = enterprise_info['sso_enforced_for_signin']
        features.sso_enforced_for_signin_protocol = enterprise_info['sso_enforced_for_signin_protocol']
        features.sso_enforced_for_web = enterprise_info['sso_enforced_for_web']
        features.sso_enforced_for_web_protocol = enterprise_info['sso_enforced_for_web_protocol']
