import asyncio
import aiohttp
from time import time
from typing import Any
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from bot.config import settings
from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers

from random import randint

from ..utils.transaction import TRANSACTION_METHODS
from ..utils.tg_manager.TGSession import TGSession


class Tapper:
    def __init__(self, tg_session: TGSession):
        self.tg_session = tg_session
        self.session_name = tg_session.session_name
        self.auth_data = ''

    async def get_strict_data(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "data": self.auth_data,
                "hash": self.tg_session.hash_value
            }
            response = await http_client.post('https://miniapp.bool.network/backend/bool-tg-interface/user/user/strict',
                                              json=json_data)
            response.raise_for_status()

            response_json = await response.json()
            await http_client.get(
                f'https://miniapp.bool.network/backend/bool-tg-interface/user/check?tgId={self.tg_session.tg_id}')
            return response_json['data']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting user strict data: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def register_user(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "data": self.auth_data,
                "hash": self.tg_session.hash_value
            }
            response = await http_client.post('https://miniapp.bool.network/backend/bool-tg-interface/user/register',
                                              json=json_data)
            response.raise_for_status()

            response_json = await response.json()
            if response_json['message'] == "success":
                logger.success(
                    f"{self.session_name} | User successfully registered | User Id: <y>{response_json['data']}</y>")

            return response_json['data']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during registration: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def do_task(self, http_client: aiohttp.ClientSession, task_name: str, task_id: int):
        try:
            logger.info(f"{self.session_name} | Performing task <lc>{task_name}</lc>...")

            json_data = {
                "assignmentId": task_id,
                "data": self.auth_data,
                "hash": self.tg_session.hash_value
            }
            response = await http_client.post(f'https://miniapp.bool.network/backend/bool-tg-interface/assignment/do',
                                              json=json_data)
            response.raise_for_status()
            response_json = await response.json()

            return response_json['data']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when processing task: {error}")
            await asyncio.sleep(delay=3)

    async def get_user_staking(self, http_client: aiohttp.ClientSession, wallet_address: str) -> list:
        try:
            payload = {
                'address': wallet_address,
                'pageNo': 1,
                'pageSize': 100,
                'yield': 1
            }
            response = await http_client.get(
                f'https://miniapp.bool.network/backend/bool-tg-interface/user/user-vote-devices',
                params=payload)
            response.raise_for_status()
            response_json = await response.json()

            return response_json['data']['records']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting user staking: {error}")
            await asyncio.sleep(delay=3)
            return []

    async def get_staking_record(self, http_client: aiohttp.ClientSession, page: int) -> dict:
        try:
            response = await http_client.get(
                f'https://miniapp.bool.network/backend/bool-tg-interface/user/vote:devices?'
                f'pageNo={page}&pageSize=20&yield=1')
            response.raise_for_status()
            response_json = await response.json()

            records = response_json['data']['records']
            for record in records:
                if record['voterCount'] < 500 and record['deviceState'] == 'SERVING':
                    return record

            if page < int(response_json['data']['pages']):
                return await self.get_staking_record(http_client, page + 1)
            else:
                logger.warning(f"{self.session_name} | Failed getting staking record")
                return None

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting records: {error}")
            await asyncio.sleep(delay=3)

    async def verify_account(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "data": self.auth_data,
                "hash": self.tg_session.hash_value
            }

            response = await http_client.post('https://miniapp.bool.network/backend/bool-tg-interface/user/verify',
                                              json=json_data)
            response.raise_for_status()
            response_json = await response.json()
            if response_json['data']:
                logger.success(f"{self.session_name} | Account Verified! Available for tBOL Airdrop")
            else:
                logger.warning(f"{self.session_name} | Failed verified account | Try next time")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when verifying account: {error}")
            await asyncio.sleep(delay=3)

    async def make_staking(self, http_client: aiohttp.ClientSession, device_id: str, amount: str):
        try:
            json_data = {
                "deviceId": [device_id],
                "amount": [amount],
                "data": self.auth_data,
                "hash": self.tg_session.hash_value
            }

            response = await http_client.post('https://miniapp.bool.network/backend/bool-tg-interface/stake/do',
                                              json=json_data)
            response.raise_for_status()
            response_json = await response.json()
            if response_json['message'] == "success":
                return response_json['data']
            else:
                logger.warning(f"{self.session_name} | Failed making stake <r>{response_json['message']}</r>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when staking: {error}")
            await asyncio.sleep(delay=3)

    async def get_unstaking_balance(self, http_client: aiohttp.ClientSession, wallet_address: str):
        try:
            chain_id = TRANSACTION_METHODS['eth_chainId']
            chain_id['id'] = 1
            get_balance = TRANSACTION_METHODS['eth_getBalance']
            get_balance['id'] = 2
            get_balance['params'][0] = wallet_address
            json_data = [chain_id, get_balance]
            response = await http_client.post('https://betatest-rpc-node-http.bool.network/',
                                              json=json_data)
            response.raise_for_status()
            transaction_data = await response.json()
            hex_balance = transaction_data[1].get('result')
            dec_balance = int(hex_balance, 16)
            return int(dec_balance / 1e18)

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting staking balance: {error}")
            await asyncio.sleep(delay=3)

    async def send_transaction_data(self, http_client: aiohttp.ClientSession, json_data: Any):
        try:
            response = await http_client.post('https://betatest-rpc-node-http.bool.network/',
                                              json=json_data)
            response.raise_for_status()
            response_json = await response.json()
            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when sending transaction data: {error}")
            await asyncio.sleep(delay=3)

    async def performing_transaction(self, http_client: aiohttp.ClientSession, data: str, wallet_address: str):
        try:
            chain_id = TRANSACTION_METHODS['eth_chainId']
            get_block_number = TRANSACTION_METHODS['eth_blockNumber']
            send_transaction = TRANSACTION_METHODS['eth_sendRawTransaction']
            get_receipt = TRANSACTION_METHODS['eth_getTransactionReceipt']
            transaction_count = TRANSACTION_METHODS['eth_getTransactionCount']
            get_by_hash = TRANSACTION_METHODS['eth_getTransactionByHash']
            get_block = TRANSACTION_METHODS['eth_getBlockByNumber']

            chain_id['id'] = 1
            get_block_number['id'] = 2
            send_transaction['id'] = 3
            send_transaction['params'] = [data]
            json_data = [chain_id, get_block_number, send_transaction]
            transaction_data = await self.send_transaction_data(http_client=http_client, json_data=json_data)
            transaction = transaction_data[2]['result']

            if transaction:
                chain_id['id'] = 4
                get_receipt['id'] = 5
                get_receipt['params'] = [transaction]
                json_data = [chain_id, get_receipt]
                await self.send_transaction_data(http_client=http_client, json_data=json_data)

                get_block_number['id'] = 6
                transaction_count['id'] = 7
                chain_id['id'] = 8
                transaction_count['params'][0] = wallet_address
                json_data = [get_block_number, transaction_count, chain_id]
                transaction_data = await self.send_transaction_data(http_client=http_client, json_data=json_data)
                block_number = transaction_data[0]['result']

                chain_id['id'] = 9
                get_by_hash['id'] = 10
                get_by_hash['params'] = [transaction]
                json_data = [chain_id, get_by_hash]
                await self.send_transaction_data(http_client=http_client, json_data=json_data)

                chain_id['id'] = 11
                get_block['id'] = 12
                get_block['params'][0] = block_number
                json_data = [chain_id, get_block]
                await self.send_transaction_data(http_client=http_client, json_data=json_data)

                chain_id['id'] = 13
                get_receipt['id'] = 14
                get_block_number['id'] = 15
                json_data = [chain_id, get_receipt, get_block_number]
                await self.send_transaction_data(http_client=http_client, json_data=json_data)

                get_block_number['id'] = 16
                json_data = [get_block_number]
                await self.send_transaction_data(http_client=http_client, json_data=json_data)

                get_block_number['id'] = 17
                transaction_count['id'] = 18
                chain_id['id'] = 19
                get_receipt['id'] = 20
                json_data = [get_block_number, transaction_count, chain_id, get_receipt]
                await self.send_transaction_data(http_client=http_client, json_data=json_data)

                chain_id['id'] = 21
                get_by_hash['id'] = 22
                json_data = [chain_id, get_by_hash]
                result_json = await self.send_transaction_data(http_client=http_client, json_data=json_data)
                return result_json[1]['result']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when performing transaction: {error}")
            await asyncio.sleep(delay=3)

    async def check_daily_reward(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "data": self.auth_data,
                "hash": self.tg_session.hash_value
            }
            response = await http_client.post(
                f'https://miniapp.bool.network/backend/bool-tg-interface/assignment/daily/list',
                json=json_data)
            response.raise_for_status()
            response_json = await response.json()

            if len(response_json['data']) > 0:
                daily_task = response_json['data'][0]
                if not daily_task.get('done'):
                    json_data['assignmentId'] = daily_task['assignmentId']
                    response = await http_client.post(
                        f'https://miniapp.bool.network/backend/bool-tg-interface/assignment/daily/do',
                        json=json_data)
                    response.raise_for_status()
                    logger.success(
                        f"{self.session_name} | Daily claimed | Reward: <e>{daily_task['reward']}</e> tBOL | "
                        f"Day count: <e>{daily_task['signDay'] + 1}</e>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when processing daily reward: {error}")
            await asyncio.sleep(delay=3)

    async def processing_tasks(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "data": self.auth_data,
                "hash": self.tg_session.hash_value
            }
            response = await http_client.post('https://miniapp.bool.network/backend/bool-tg-interface/assignment/list',
                                              json=json_data)
            response.raise_for_status()
            response_json = await response.json()

            tasks = response_json['data']
            for task in tasks:
                if not task['done'] and task['project'] != 'daily' and 'Boost' not in task['title']:
                    if 'Join' or 'Subscribe' in task['title'] and 'https://t.me/' in task['url']:
                        if settings.JOIN_TG_CHANNELS:
                            logger.info(f"{self.session_name} | Performing TG subscription to <lc>{task['url']}</lc>")
                            await self.tg_session.join_tg_channel(task['url'])
                        else:
                            continue
                    await asyncio.sleep(delay=randint(5, 15))
                    status = await self.do_task(http_client, task['title'], int(task['assignmentId']))
                    if status:
                        logger.success(f"{self.session_name} | Task <lc>{task['title']}</lc> - Completed | "
                                       f"Reward: <e>{task['reward']}</e> tBOL")
                    else:
                        logger.warning(f"{self.session_name} | Failed processing task <lc>{task['title']}</lc>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when processing tasks: {error}")
            await asyncio.sleep(delay=3)

    async def check_user_subscription(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "data": self.auth_data,
                "hash": self.tg_session.hash_value
            }
            response = await http_client.post(
                'https://miniapp.bool.network/backend/bool-tg-interface/user/channel/joined',
                json=json_data)
            response.raise_for_status()
            response_json = await response.json()

            return response_json['data']

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when checking tg subscription: {error}")
            await asyncio.sleep(delay=3)

    async def run(self, user_agent: str, proxy: str | None) -> None:
        access_token_created_time = 0
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
        headers["User-Agent"] = user_agent
        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)

        token_live_time = randint(3500, 3600)
        while True:
            try:
                sleep_time = randint(settings.SLEEP_TIME[0], settings.SLEEP_TIME[1])
                if time() - access_token_created_time >= token_live_time:
                    self.auth_data = await self.tg_session.get_tg_web_data()
                    if self.auth_data is None:
                        await asyncio.sleep(delay=randint(30, 60))
                        continue
                    access_token_created_time = time()
                    token_live_time = randint(3500, 3600)

                    strict_data = await self.get_strict_data(http_client=http_client)
                    if strict_data is None:
                        await asyncio.sleep(delay=randint(1, 3))
                        user_id = await self.register_user(http_client=http_client)
                        if user_id is not None:
                            strict_data = await self.get_strict_data(http_client=http_client)

                    balance = strict_data['rewardValue']
                    rank = strict_data['rank']
                    logger.info(f"{self.session_name} | Balance: <e>{balance}</e> tBOL | "
                                f"Rank: <fg #ffbcd9>{rank}</fg #ffbcd9> | "
                                f"Is available for Airdrop: <lc>{strict_data['isVerify']}</lc>")

                    await self.check_daily_reward(http_client=http_client)

                    if settings.AUTO_TASK:
                        await asyncio.sleep(delay=randint(3, 5))
                        await self.processing_tasks(http_client=http_client)

                    await asyncio.sleep(delay=randint(3, 5))

                    balance = await self.get_unstaking_balance(http_client=http_client,
                                                               wallet_address=strict_data['evmAddress'])
                    user_staking = await self.get_user_staking(http_client=http_client,
                                                               wallet_address=strict_data['evmAddress'])
                    staking_balance = 0
                    for record in user_staking:
                        staking_balance += int(int(record['currentStake']) / 1e18)
                    logger.info(f'{self.session_name} | Balance in stake: <e>{staking_balance}</e> tBOL | '
                                f'Unused balance: <fg #FFA500>{balance}</fg #FFA500> tBOL')

                    if settings.STAKING and balance >= settings.MIN_STAKING_BALANCE:
                        if (user_staking is None or len(user_staking) == 0 and not strict_data['isVerify']) \
                                or strict_data['isVerify'] and settings.STAKE_ALL:
                            record = await self.get_staking_record(http_client=http_client, page=1)
                            if record is not None:
                                voters = record['voterCount']
                                apy = round(record['yield'] * 100, 2)
                                logger.info(
                                    f'{self.session_name} | Staking record found | APY: <lc>{apy}%</lc> | '
                                    f'Voters: <y>{voters}</y>')
                                await asyncio.sleep(delay=randint(3, 5))
                                data = await self.make_staking(http_client=http_client,
                                                               device_id=record['deviceID'], amount=balance)
                                if data is not None:
                                    await asyncio.sleep(delay=randint(3, 5))
                                    result = await self.performing_transaction(http_client=http_client,
                                                                               data=data,
                                                                               wallet_address=strict_data[
                                                                                   'evmAddress'])
                                    if result is not None:
                                        logger.success(
                                            f"{self.session_name} | Successfully staked <e>{balance}</e> tBOL")

                    if not strict_data['isVerify'] and staking_balance > 0:
                        await asyncio.sleep(delay=randint(3, 10))
                        subscribed = await self.check_user_subscription(http_client=http_client)
                        if not subscribed:
                            await self.tg_session.join_tg_channel('https://t.me/boolofficial')
                        else:
                            await self.verify_account(http_client=http_client)

                logger.info(f"{self.session_name} | Sleep <y>{round(sleep_time / 60, 1)}</y> min")
                await asyncio.sleep(delay=sleep_time)

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=randint(60, 120))

            except KeyboardInterrupt:
                logger.warning("<r>Bot stopped by user...</r>")
            finally:
                if http_client is not None:
                    await http_client.close()


async def run_tapper(tg_session: TGSession, user_agent: str, proxy: str | None):
    try:
        await Tapper(tg_session=tg_session).run(user_agent=user_agent, proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_session.session_name} | Invalid Session")
