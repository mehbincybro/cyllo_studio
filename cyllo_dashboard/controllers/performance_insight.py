# -*- coding: utf-8 -*-
from odoo import http
import psutil
import subprocess
from odoo.tools import config
import platform
from odoo.http import request


class PerformanceController(http.Controller):
    """Controller for managing system performance data."""

    @http.route('/performance', methods=['POST'], type='json', auth='user', csrf=False)
    def get_performance(self):
        """System performances"""
        sorted_tuples = ()
        storage = psutil.virtual_memory()
        total_cpu_usage = psutil.cpu_percent(4)
        used_ram_percent = storage.percent
        total_ram = round(storage.total / (1024.0 ** 3), 2)
        available_ram = round(storage.available / (1024.0 ** 3), 2)
        used_ram_gb = round(total_ram - available_ram, 2)
        hdd = psutil.disk_usage('/')
        used_memory = round((hdd.used / 1000000000), 2)
        free_memory = round((hdd.free / 1000000000), 2)
        total_memory = round((used_memory + free_memory), 2)
        total_virtual_memory_kb = total_ram * 1000000
        get_load_avg = psutil.getloadavg()
        try:
            temperatures = psutil.sensors_temperatures(fahrenheit=False)
            hardware_temperature = round(temperatures['k10temp'][0].current) if ('k10temp' in temperatures) else 0
        except AttributeError:
            hardware_temperature = 0

        """CPU core wise usages"""
        cpu_usage = psutil.cpu_percent(percpu=True)
        core_usage_list = []
        for i, usage in enumerate(cpu_usage):
            cpu_core_usage = f"Core {i}: {usage}"
            core_usage_list.append(cpu_core_usage)
        """Most memory using programs"""
        try:
            processes = psutil.process_iter(['name', 'memory_info', 'pid'])
            program_memory_list = []
            ram_processes = sorted(processes, key=lambda a: a.memory_info().rss if psutil.pid_exists(a.pid) else 0.0,
                                   reverse=True)[:4]
            for process in ram_processes:
                try:
                    process_name = process.name()
                    memory_info = process.memory_info().rss
                    if memory_info is not None:
                        program_memory = {
                            process_name: round(((memory_info * 0.001) / total_virtual_memory_kb) * 100, 2)
                        }
                        program_memory_list.append(program_memory)
                except psutil.AccessDenied:
                    # Access to process denied, skip it
                    pass

            result_dict = {}
            for dictionary in program_memory_list:
                for key, value in dictionary.items():
                    if key in result_dict:
                        if value > result_dict[key]:
                            result_dict[key] = value
                    else:
                        result_dict[key] = value

            tuples = list(result_dict.items())
            sorted_tuples = sorted(tuples, key=lambda x: x[1], reverse=True)
        except psutil.AccessDenied:
            pass
        """Periodical datas"""
        request.env['performance.history'].create({
            'used_memory_history': used_memory,
            'used_ram_history': used_ram_gb,
            'hardware_temperature_history': hardware_temperature,
            'cpu_usage_history': total_cpu_usage,
        })

        used_memory_history = []
        used_ram_history = []
        hardware_temperature_history = []
        cpu_usage_history = []
        for value in request.env['performance.history.time'].search([]):
            used_memory_date = [value.create_date.date(), value.used_memory_history]
            used_ram_date = [value.create_date.date(), value.used_ram_history]
            hardware_temperature_date = [value.create_date.date(), value.hardware_temperature_history]
            cpu_usage_time = [value.create_date.date(), value.cpu_usage_history]
            used_memory_history.append(used_memory_date)
            used_ram_history.append(used_ram_date)
            hardware_temperature_history.append(hardware_temperature_date)
            cpu_usage_history.append(cpu_usage_time)
        """Operating System information"""
        os_dict = {
            'operating_system': platform.system(),
            'system_release_version': platform.version(),
            'platform_processor': platform.processor(),
            'platform_architecture': platform.architecture()
        }
        """Odoo configuration data"""
        conf_dict = {
            'db_name': config.get('db_name'),
            'db_user': config.get('db_user'),
            'osv_memory_count_limit': config.get('osv_memory_count_limit'),
            'transient_age_limit': config.get('transient_age_limit'),
            'limit_memory_hard': round((config.get('limit_memory_hard') / 1000000000), 2),
            'limit_memory_soft': round((config.get('limit_memory_soft') / 1000000000), 2),
            'limit_request': config.get('limit_request'),
            'limit_time_cpu': config.get('limit_time_cpu'),
            'limit_time_real': config.get('limit_time_real'),
            'max_cron_threads': config.get('max_cron_threads'),
            'workers': config.get('workers'),
            'http_port': config.get('http_port'),
            'addons_path': config.get('addons_path'),
        }
        return {
            'is_admin': request.env.is_admin(),
            'cpu': core_usage_list,
            'total_cpu_usage': total_cpu_usage,
            'most_memory_using_programs': sorted_tuples,
            'ram_percent': used_ram_percent,
            'ram_in_gb': used_ram_gb,
            'total_ram': total_ram,
            'available_ram': available_ram,
            'used_memory': used_memory,
            'free_memory': free_memory,
            'total_memory': total_memory,
            'get_load_avg': get_load_avg,
            'hardware_temperature': hardware_temperature,
            'conf_dict': conf_dict,
            'os_dict': os_dict,
            'used_memory_history': used_memory_history[-10:],
            'used_ram_history': used_ram_history[-10:],
            'hardware_temperature_history': hardware_temperature_history[-10:],
            'cpu_usage_history': cpu_usage_history[-10:],
        }

    @http.route('/cpu', methods=['POST'], type='json', auth='user', csrf=False)
    def get_cpu_performance(self):
        """Most using CPU using programs"""
        top_output = subprocess.run(["top", "-b", "-n", "1"], capture_output=True).stdout.decode()
        lines = top_output.split("\n")
        process_lines = lines[7:]
        cpu_usage = {}
        for line in process_lines:
            if not line.strip():
                continue
            parts = line.split()
            command = parts[-1]
            cpu_percent = parts[8]
            cpu_usage[command] = float(cpu_percent)
        dic_out = {x: y for x, y in cpu_usage.items() if x != 'top' and y != 0}
        key_value_pairs = [(key, value) for key, value in dic_out.items()]
        """CPU core wise usages"""
        cpu_usage = psutil.cpu_percent(percpu=True)
        core_usage_list = []
        for i, usage in enumerate(cpu_usage):
            cpu_core_usage = f"Core {i}: {usage}"
            core_usage_list.append(cpu_core_usage)
        return {
            'program_cpu_usage_list': key_value_pairs[:3],
            'cpu_core_usage': core_usage_list
        }
