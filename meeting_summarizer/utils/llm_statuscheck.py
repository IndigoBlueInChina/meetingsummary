import requests

class LLMStatusChecker:
    def __init__(self, service_url):
        self.service_url = service_url

    def check_status(self):
        try:
            response = requests.get(self.service_url)
            if response.status_code == 200:
                return "ready"
            else:
                return "offline"
        except requests.ConnectionError:
            return "offline"
        except Exception as e:
            print(f"Error checking LLM status: {str(e)}")
            return "offline"

# Example usage
# checker = LLMStatusChecker('http://your-llm-service-url')
# status = checker.check_status()
# print(status)  # Outputs: 'ready' or 'offline'