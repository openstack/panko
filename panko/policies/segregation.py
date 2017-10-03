# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_policy import policy

rules = [
    policy.DocumentedRuleDefault(
        name='segregation',
        check_str='rule:context_is_admin',
        description='Return the user and project the request'
                    'should be limited to',
        operations=[
            {
                'path': '/v2/events',
                'method': 'GET'
            },
            {
                'path': '/v2/events/{message_id}',
                'method': 'GET'
            }
        ]
    )
]


def list_rules():
    return rules
