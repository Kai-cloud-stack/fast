# _*_coding:utf-8_*_
"""
@statement: Copyright(c) 2024 FreeTech Automated Testing CO.LTD
@file     : temp_main
@date     : 2025/8/13 
@author   : <kai.ren@freetech.com>
@describe : 
"""
import json
import time
from pprint import pprint

from test_framework.checkers.environment_checker import EnvironmentChecker
from test_framework.interfaces.canoe_interface import CANoeInterface


def run_tasks(canoe_obj, task_config):
    with open(task_config, encoding='utf8') as f:
        json_file = json.loads(f.read())
        task = [i for i in json_file['test_cases'] if i['enabled']]
        enable_case = [testcase['name'] for testcase in task]
        canoe_obj.select_test_cases(enable_case)
        canoe_obj.start_measurement()
        canoe_obj.run_test_modules()
        canoe_obj.stop_measurement()
        results = canoe_obj.test_results
        # print([result for result in results if results.result != "SKIP"])
        return results


def main(config, task):
    with open(config) as f:
        config = json.loads(f.read())
        canoe = CANoeInterface(canoe_config=config)
        # non = NotificationService()
        tester = EnvironmentChecker(canoe, None)
        tester.check_environment()
        env_res = tester.get_check_results()
        res = ''
        for i in env_res:
            if i.test_case == 'Check_Environment':
                res = i.result.name
        if res == "PASS":
            start_time = time.time()
            res = run_tasks(canoe, task_config)
            end_time = time.time()
            spend_time = end_time - start_time
            print(f"共花费%:  {spend_time} S")
            for i in res:
                if i.result.name != 'SKIP':
                    pprint(i)


if __name__ == '__main__':
    main_config = r'E:\A-code\fast\fast\test_framework\config\main_config.json'
    task_config = r'E:\A-code\fast\fast\test_framework\config\task_config.json'
    main(main_config, task_config)
    # run_tasks(main_config, task_config)


