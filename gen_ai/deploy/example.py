"""
This module provides an example on how to call Talk2Docs API. 
It uses fake data as member_context_full
"""

import requests


def main():
    """This is main function that serves as an example how to use the respond API method"""
    url = "http://127.0.0.1:8080/respond/"
    data = {
        "question": "I injured my back. Is massage therapy covered?",
        "member_context_full": {"set_number": "001acis", "member_id": "1234"},
    }

    response = requests.post(url, json=data, timeout=3600)

    if response.status_code == 200:
        print("Success!")
        print(response.json())  # This will print the response data
    else:
        print("Error:", response.status_code)
        print(response.text)  # This will print the error message, if any


if __name__ == "__main__":
    main()
