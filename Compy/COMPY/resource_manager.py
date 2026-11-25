import psutil
import platform

class GetMachineInfo:
    
    def get_cpu_info(self):
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "cpu_count": psutil.cpu_count(logical=True)
        }

    def get_memory_info(self, Size = 3):
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024 ** Size), 2),
            "used_gb": round(mem.used / (1024 ** Size), 2),
            "percent": mem.percent
        }

    def get_machine_status(self):
        battery = psutil.sensors_battery()
        return {
            "pct": battery.percent,
            "plugged_in": battery.power_plugged,
            "os": platform.system(),
            "release": platform.release(),
        } if battery else None
