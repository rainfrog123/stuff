from user_proxy_config import UserProxyConfig
from fingerprint_config import FingerprintConfig

class Profile:
    def __init__(self, name=None, group_id=None, domain_name=None, repeat_config=None, country=None,
                 fingerprint_config=None, open_urls=None, username=None, password=None, fakey=None, cookie=None,
                 ignore_cookie_error=None, ip=None, region=None, city=None, remark=None, ipchecker=None,
                 sys_app_cate_id=None, user_proxy_config=None, proxyid=None):
        self.name = name
        self.group_id = group_id  # Necessary parameter
        self.domain_name = domain_name
        self.repeat_config = repeat_config
        self.country = country
        self.fingerprint_config = fingerprint_config  # Necessary parameter
        self.open_urls = open_urls
        self.username = username
        self.password = password
        self.fakey = fakey
        self.cookie = cookie
        self.ignore_cookie_error = ignore_cookie_error
        self.ip = ip
        self.region = region
        self.city = city
        self.remark = remark
        self.ipchecker = ipchecker
        self.sys_app_cate_id = sys_app_cate_id
        self.user_proxy_config = user_proxy_config  # Either this or proxyid is required
        self.proxyid = proxyid  # Either this or user_proxy_config is required

    def to_dict(self):
        payload = {
            "name": self.name,
            "group_id": self.group_id,
            "domain_name": self.domain_name,
            "repeat_config": self.repeat_config,
            "country": self.country,
            "fingerprint_config": self.fingerprint_config.to_dict() if self.fingerprint_config else None,
            "user_proxy_config": self.user_proxy_config.to_dict() if self.user_proxy_config else None
        }

        # Optional parameters
        if self.open_urls:
            payload["open_urls"] = self.open_urls
        if self.username:
            payload["username"] = self.username
        if self.password:
            payload["password"] = self.password
        if self.fakey:
            payload["fakey"] = self.fakey
        if self.cookie:
            payload["cookie"] = self.cookie
        if self.ignore_cookie_error is not None:
            payload["ignore_cookie_error"] = self.ignore_cookie_error
        if self.ip:
            payload["ip"] = self.ip
        if self.region:
            payload["region"] = self.region
        if self.city:
            payload["city"] = self.city
        if self.remark:
            payload["remark"] = self.remark
        if self.ipchecker:
            payload["ipchecker"] = self.ipchecker
        if self.sys_app_cate_id:
            payload["sys_app_cate_id"] = self.sys_app_cate_id
        if self.proxyid:
            payload["proxyid"] = self.proxyid

        return payload

# Example usage
user_proxy_config_example = UserProxyConfig(proxy_soft='no_proxy')

finger_print_config_example = FingerprintConfig()

profile_example = Profile(
    name='test1',
    group_id='4683840',
    fingerprint_config=finger_print_config_example,
    user_proxy_config=user_proxy_config_example
)
