#
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

"""support big integer traits

Revision ID: c3955547bff2
Revises:
Create Date: 2017-07-18 22:03:44.996571

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3955547bff2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('trait_int', "value", type_=sa.BigInteger)
