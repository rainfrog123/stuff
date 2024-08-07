import json
class UserProxyConfig:
    """
    Configuration for account proxy settings.

    Attributes:
        proxy_soft (str): Proxy software being used. This is required. Default is None.
                        Supported values: "luminati", "lumauto", "oxylabsauto", "922S5auto", "ipideaauto",
                        "ipfoxyauto", "922S5auth", "kookauto", "ssh", "other", "no_proxy".
        proxy_type (str): Type of proxy protocol. Default is None.
                        Supported values: "http", "https", "socks5". For "no_proxy", this can be omitted.
        proxy_host (str): Address of the proxy server. Default is None.
                        Can be a domain name or IP address. For "no_proxy", this can be omitted.
        proxy_port (str): Port of the proxy server. Default is None.
                        For "no_proxy", this can be omitted.
        proxy_user (str): Proxy account name. Default is None.
        proxy_password (str): Proxy account password. Default is None.
        proxy_url (str): The link to change IP, used for mobile proxies. Supports "http", "https", "socks5". Default is None.
                        1. Can change proxy IP address via the link.
                        2. If multiple profiles share the same proxy settings, their IP addresses will change simultaneously.
        global_config (str): Information on the list of accounts managed using the proxy. Default is "0".
                        - "0": Default
                        - "1": Specific global configuration
    """
    def __init__(self, proxy_soft, proxy_type=None, proxy_host=None, proxy_port=None, proxy_user=None, proxy_password=None, proxy_url=None, global_config="0"):
        self.proxy_soft = proxy_soft
        self.proxy_type = proxy_type
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_user = proxy_user
        self.proxy_password = proxy_password
        self.proxy_url = proxy_url
        self.global_config = global_config

    def to_dict(self):
        return {
            "proxy_soft": self.proxy_soft,
            "proxy_type": self.proxy_type,
            "proxy_host": self.proxy_host,
            "proxy_port": self.proxy_port,
            "proxy_user": self.proxy_user,
            "proxy_password": self.proxy_password,
            "proxy_url": self.proxy_url,
            "global_config": self.global_config
        }

# Example usage
user_proxy_config_example = UserProxyConfig(
    proxy_soft="luminati",
    proxy_type="http",
    proxy_host="pr.oxylabs.io",
    proxy_port="123",
    proxy_user="abc",
    proxy_password="xyz"
)

print(json.dumps(user_proxy_config_example.to_dict(), indent=4))
