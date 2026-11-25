import asyncio
from desktop_notifier import DesktopNotifier, DEFAULT_SOUND
from SQL_interface import FixSQL
from resource_manager import GetMachineInfo
import time


database = FixSQL("machine1.db", "AcerLaptop")
running = True
machine = GetMachineInfo()
notifier = DesktopNotifier(app_name="COMPY")
async def main():
    while running:
        machine_data = {
                    'CPU':machine.get_cpu_info(),
                    'RAM': machine.get_memory_info(),
                    'device': machine.get_machine_status()
                }
        database.new_machine_data(machine_data['CPU'],
                                machine_data['RAM'],
                                machine_data['device']
                                )
        if (machine_data['CPU']['cpu_percent'] > 90 or machine_data['RAM']['percent'] > 90):
            await notifier.send(
            title="CPU Overload",
            message=f"CPU: {machine_data['CPU']['cpu_percent']}! \n RAM:{machine_data['RAM']['percent']}",
            sound=DEFAULT_SOUND
        )
        time.sleep(0.5)
        print(database.show_table())

if __name__ == "__main__":
    asyncio.run(main())
