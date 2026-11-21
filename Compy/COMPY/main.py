import asyncio
import json
import time
from datetime import datetime
from fastapi import FastAPI, Query
from nicegui import ui
from resource_manager import GetMachineInfo
from SQL_interface import FixSQL

app = FastAPI()
database = FixSQL("machine1.db", "AcerLaptop")
machine = GetMachineInfo()


@app.get('/metrics/{metric}/')
def metrics(metric: str, size: int = Query(default=3, le=5, ge=2)):
    current_time = datetime.now().isoformat(sep=' ', timespec='seconds')
    machine_data = {
        'CPU': machine.get_cpu_info(),
        'RAM': machine.get_memory_info(size),
        'disk': machine.get_disk_info(size),
        'network': machine.get_disk_info(size),
        'device': machine.get_machine_status(),
    }
    if metric == "machine":
        return [machine_data, current_time]
    elif metric == "history":
        return database.show_table()
    else:
        return [machine_data[metric], current_time]


def pie_chart():
    return {
        'color': ['#CFEE9E', '#1E2019'],
        'series': [{
            'type': 'pie',  # type of chart
            'radius': ['65%', '85%'],  # chart size(do not touch)

            'label': {
                'show': True,
                'position': 'center',
                'formatter': '40%',
                'fontSize': 28,
                'fontWeight': 'bold',
                'color': '#CFEE9E',
            },

            # chart placeholder values
            'data': [
                {'value': 10, 'name': 'A'},
                {'value': 10, 'name': 'B'},
            ],
        }],
    }


def collect_snapshot() -> dict:
    return {
        'CPU': machine.get_cpu_info(),
        'RAM': machine.get_memory_info(2),
        'disk': machine.get_disk_info(2),
        'network': machine.get_disk_info(2),
        'device': machine.get_machine_status(),
    }


@ui.page("/main")
async def main_page():
    ui.query('body').classes('bg-[#2d3528] text-[#CFEE9E] font-mono')

    active_filter = {'metric': 'ALL'}
    last_alert_ts = {'CPU': 0.0, 'RAM': 0.0}
    alert_cooldown_sec = 30.0

    with ui.column().classes('w-full max-w-6xl mx-auto p-6 gap-6'):

        with ui.row().classes(
            'w-full items-center gap-4 pb-3 border-b-[3px] border-[#CFEE9E]'
        ):
            ui.label('COMPY').classes('text-3xl font-bold text-[#CFEE9E]')
            ui.label('SYS').classes(
                'w-10 h-10 rounded-full border-2 border-[#CFEE9E] '
                'flex items-center justify-center text-xs font-bold text-[#CFEE9E]'
            )

        with ui.grid().classes('w-full grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4'):
            with ui.column().classes(
                'items-center justify-center bg-[#21271e] border border-[#3f4d37] '
                'rounded-lg p-4 gap-2'
            ):
                ui.label('CPU').classes('text-base font-bold text-[#CFEE9E]')
                CPU = ui.echart(options=pie_chart()).classes('w-32 h-32')
            with ui.column().classes(
                'items-center justify-center bg-[#21271e] border border-[#3f4d37] '
                'rounded-lg p-4 gap-2'
            ):
                ui.label('RAM').classes('text-base font-bold text-[#CFEE9E]')
                RAM = ui.echart(options=pie_chart()).classes('w-32 h-32')
            with ui.column().classes(
                'items-center justify-center bg-[#21271e] border border-[#3f4d37] '
                'rounded-lg p-4 gap-2'
            ):
                ui.label('DISK').classes('text-base font-bold text-[#CFEE9E]')
                DISK = ui.echart(options=pie_chart()).classes('w-32 h-32')
            with ui.column().classes(
                'items-center justify-center bg-[#21271e] border border-[#3f4d37] '
                'rounded-lg p-4 gap-2'
            ):
                ui.label('NETWORK').classes('text-base font-bold text-[#CFEE9E]')
                NETWORK = ui.echart(options=pie_chart()).classes('w-32 h-32')

        with ui.grid().classes('w-full grid-cols-1 md:grid-cols-3 gap-5 items-start'):
            with ui.column().classes(
                'md:col-span-2 w-full bg-[#21271e] border border-[#3f4d37] rounded-lg p-5 gap-3'
            ):
                ui.label('HISTORY').classes('text-xl font-bold text-[#CFEE9E]')

                filter_buttons: dict[str, ui.button] = {}

                def select_filter(metric_name: str):
                    active_filter['metric'] = metric_name
                    for key, btn in filter_buttons.items():
                        if key == metric_name:
                            btn.classes(
                                replace='bg-[#CFEE9E] text-[#21271e] border border-[#CFEE9E] '
                                        'px-2.5 py-1 rounded text-xs font-bold'
                            )
                        else:
                            btn.classes(
                                replace='bg-[#3c4735] text-[#CFEE9E] border border-[#58694e] '
                                        'px-2.5 py-1 rounded text-xs'
                            )
                    refresh_history()

                with ui.row().classes('items-center flex-wrap gap-1.5'):
                    ui.label('FILTER:').classes('text-xs text-[#CFEE9E] mr-1')
                    for m in ['ALL', 'CPU', 'RAM', 'DISK', 'NET']:
                        is_default = m == 'ALL'
                        cls = (
                            'bg-[#CFEE9E] text-[#21271e] border border-[#CFEE9E] '
                            'px-2.5 py-1 rounded text-xs font-bold'
                            if is_default
                            else 'bg-[#3c4735] text-[#CFEE9E] border border-[#58694e] '
                            'px-2.5 py-1 rounded text-xs'
                        )
                        filter_buttons[m] = ui.button(
                            m, on_click=lambda _, metric=m: select_filter(metric)
                        ).props('flat dense').classes(cls)

                history_container = ui.column().classes('w-full gap-0 mt-1')

            with ui.column().classes(
                'md:col-span-1 w-full bg-[#21271e] border border-[#3f4d37] rounded-lg p-5 gap-3'
            ):
                ui.label('ALERTS').classes('text-xl font-bold text-[#CFEE9E]')
                alerts_container = ui.column().classes('w-full gap-2.5')

    def add_alert_item(metric_name: str, pct_val: float):
        now = datetime.now()
        stamp = now.strftime('%H:%M, %b %d %Y').upper()
        rounded_pct = round(pct_val, 1)

        ui.notify(
            f'{metric_name} is over 90% ({rounded_pct}%)!',
            type='warning',
            position='top-right',
        )

        with alerts_container:
            item = ui.column().classes(
                'w-full bg-[#384232] border-l-4 border-[#ff7b6b] rounded p-2.5 gap-1'
            ).move(alerts_container, target_index=0)
            with item:
                ui.label(stamp).classes('text-[11px] text-[#98b382]')
                with ui.row().classes('items-center gap-1 text-xs text-[#CFEE9E]'):
                    ui.label(f'{metric_name} Spiked to')
                    ui.label(f'{rounded_pct}%').classes('font-bold')

    def check_high_usage(cpu_pct: float, ram_pct: float):
        now_epoch = time.monotonic()
        for metric_name, val in (('CPU', cpu_pct), ('RAM', ram_pct)):
            if val > 90.0 and (now_epoch - last_alert_ts[metric_name]) >= alert_cooldown_sec:
                last_alert_ts[metric_name] = now_epoch
                add_alert_item(metric_name, val)

    def set_chart_value(graph, raw_val):
        pct = max(0.0, min(100.0, float(raw_val)))
        opts = pie_chart()
        graph.options['color'] = opts['color']
        graph.options['series'][0]['data'] = [
            {'value': round(pct, 1), 'name': 'A'},
            {'value': round(100.0 - pct, 1), 'name': 'B'},
        ]
        graph.options['series'][0]['label']['formatter'] = f"{round(pct)}%"
        graph.update()

    def refresh_history():
        rows = database.show_table()

        selected = active_filter['metric']
        entries_to_render = []

        for row in reversed(rows):
            _, cpu_raw, ram_raw, disk_raw, net_raw, _, ts = row
            ts_str = str(ts)

            cpu_d = json.loads(cpu_raw)
            ram_d = json.loads(ram_raw)
            disk_d = json.loads(disk_raw)
            net_d = json.loads(net_raw)

            hhmm = ts_str[11:16] if len(ts_str) >= 16 else ts_str
            row_metrics = [
                ('CPU', cpu_d.get('cpu_percent', 0)),
                ('RAM', ram_d.get('percent', 0)),
                ('DISK', disk_d.get('percent', 0)),
                ('NET', net_d.get('percent', 0)),
            ]

            for label, raw_pct in row_metrics:
                if selected == 'ALL' or selected == label:
                    entries_to_render.append((hhmm, raw_pct, label))

            if len(entries_to_render) >= 16:
                break

        history_container.clear()
        with history_container:
            if not entries_to_render:
                ui.label('No matching history records.').classes('text-xs text-[#98b382] py-2')
                return

            for hhmm, raw_pct, label in entries_to_render[:16]:
                clamped = max(0, min(100, round(float(raw_pct))))
                with ui.row().classes(
                    'w-full items-center gap-3 py-2 border-b border-[#2d3528] text-xs'
                ):
                    ui.label(hhmm).classes('text-[#CFEE9E] shrink-0')
                    with ui.element('div').classes(
                        'flex-1 h-1.5 bg-[#171c14] rounded overflow-hidden'
                    ):
                        ui.element('div').classes('h-full bg-[#CFEE9E]').style(f'width: {clamped}%')
                    ui.label(label).classes('font-bold text-[#CFEE9E] w-10 text-right shrink-0')

    async def tick_all():
        data = await asyncio.to_thread(collect_snapshot)
        await asyncio.to_thread(
            database.new_machine_data,
            data['CPU'],
            data['RAM'],
            data['disk'],
            data['network'],
            data['device'],
        )

        cpu_val = float(data['CPU']['cpu_percent'])
        ram_val = float(data['RAM']['percent'])
        disk_val = float(data['disk']['percent'])
        net_val = float(data['network']['percent'])

        set_chart_value(CPU, cpu_val)
        set_chart_value(RAM, ram_val)
        set_chart_value(DISK, disk_val)
        set_chart_value(NETWORK, net_val)

        check_high_usage(cpu_val, ram_val)
        refresh_history()

    refresh_history()
    ui.timer(3.0, tick_all)


ui.run_with(
    app, storage_secret="3"
)