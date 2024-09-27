# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
