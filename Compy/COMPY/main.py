import asyncio
import json
import time
from datetime import datetime
from fastapi import FastAPI, Query
from nicegui import app as nicegui_app, ui
from resource_manager import GetMachineInfo
from SQL_interface import FixSQL

app = FastAPI()
database = FixSQL("machine1.db", "AcerLaptop")
machine = GetMachineInfo()

REFRESH = 1       #<- AAAAAAAAAAAAA-> live CPU/RAM gauges (display only, no DB writes)
MAX_HISTORY_ROWS = 48 # bi-hour (2x24=48)


# API endpoints for getting raw values
@app.get('/metrics/{metric}/')
def metrics(metric: str, size: int = Query(default=3, le=5, ge=2)):
     # size = memory unit: 2 = MB, 3 = GB (default). le=5 & ge=2 means "only allow 2 to 5"
    current_time = datetime.now().isoformat(sep=' ', timespec='seconds')

    machine_data = {
        'CPU': machine.get_cpu_info(),
        'RAM': machine.get_memory_info(size),
        'device': machine.get_machine_status(),
    }

    if metric == "machine": # get all data
        return [machine_data, current_time]
    elif metric == "history": # show database history
        return database.show_table()
    else:
        return [machine_data[metric], current_time] # get specific metric

# create pichart function
def pie_chart():
    # send pichart object
    return {
        'color': ['#CFEE9E', '#1E2019'], 
        'series': [{
            'type': 'pie',
            'radius': ['65%', '85%'],
            'label': {
                'show': True,
                'position': 'center',
                'formatter': '40%',
                'fontSize': 28,
                'fontWeight': 'bold',
                'color': '#CFEE9E',
            },
            'data': [
                # placeholder values
                {'value': 10, 'name': 'A'},
                {'value': 10, 'name': 'B'},
            ],
        }],
    }

# create machine data function
def machine_data() -> dict:
    # Return machine processing data
    return {
        'CPU': machine.get_cpu_info(),
        'RAM': machine.get_memory_info(),
        'device': machine.get_machine_status(),
    }


# webpage itself
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
            ui.label('COMPY').classes('text-3xl font-bold text-[#CFEE9E]') # Display COMPY
            ui.label('SYS').classes( # Display SYS
                'w-10 h-10 rounded-full border-2 border-[#CFEE9E] '
                'flex items-center justify-center text-xs font-bold text-[#CFEE9E]'
            )

        # basic Grid for CPU and RAM
        with ui.grid().classes('w-full grid-cols-1 sm:grid-cols-2 md:grid-cols-2 gap-4'): 
            with ui.column().classes(
                'items-center justify-center bg-[#21271e] border border-[#3f4d37] rounded-lg p-6 gap-2'):
                ui.label('CPU').classes('text-base font-bold text-[#CFEE9E]')
                CPU = ui.echart(options=pie_chart()).classes('w-32 h-32') # enable CPU chart

            with ui.column().classes(
                'items-center justify-center bg-[#21271e] border border-[#3f4d37] rounded-lg p-6 gap-2'):
                ui.label('RAM').classes('text-base font-bold text-[#CFEE9E]')
                RAM = ui.echart(options=pie_chart()).classes('w-32 h-32') # enable RAM chart

        # data history
        with ui.grid().classes('w-full grid-cols-1 md:grid-cols-3 gap-5 items-start'):
            with ui.column().classes('md:col-span-2 w-full bg-[#21271e] border border-[#3f4d37] rounded-lg p-5 gap-3'):
                ui.label('HISTORY').classes('text-xl font-bold text-[#CFEE9E]') # Display 'HISTORY'

                filter_buttons: dict[str, ui.button] = {} # create empty dictionary for button elements

                def select_filter(metric_name: str):
                    active_filter['metric'] = metric_name  # set active data filter
                    for key, btn in filter_buttons.items():
                        # button dim feature
                        if key == metric_name:
                            btn.classes(
                                replace='bg-[#CFEE9E] text-[#21271e] border border-[#CFEE9E] px-2.5 py-1 rounded text-xs font-bold')
                        else:
                            btn.classes(
                                replace='bg-[#3c4735] text-[#CFEE9E] border border-[#58694e] px-2.5 py-1 rounded text-xs')
                    refresh_history() # redraw history

                # Draw history
                with ui.row().classes('items-center flex-wrap gap-1.5'):
                    ui.label('FILTER:').classes('text-xs text-[#CFEE9E] mr-1')
                    for m in ['ALL', 'CPU', 'RAM']:
                        is_default = m == 'ALL' # check if data is default (returns boolean)
                        element_desin = ('bg-[#CFEE9E] text-[#21271e] border border-[#CFEE9E] px-2.5 py-1 rounded text-xs font-bold' if is_default
                            else 'bg-[#3c4735] text-[#CFEE9E] border border-[#58694e] px-2.5 py-1 rounded text-xs')

                        # lock m value
                        filter_buttons[m] = ui.button(m, on_click=lambda _, metric=m: select_filter(metric)).props('flat dense').classes(element_desin)

                # search input
                search_box = ui.input(placeholder='Search date, time or %  (e.g. 2026-11-25, 14:30, 95)', on_change=lambda _: refresh_history()).props('dense outlined clearable debounce=300 input-class="text-[#CFEE9E]"').classes('w-full text-xs')

                history_container = ui.column().classes('w-full gap-0 mt-1')

            with ui.column().classes(
                'md:col-span-1 w-full bg-[#21271e] border border-[#3f4d37] rounded-lg p-5 gap-3'
            ):
                ui.label('ALERTS').classes('text-xl font-bold text-[#CFEE9E]')
                alerts_container = ui.column().classes('w-full gap-2.5')

    # alert effects
    def alert_system(metric_name: str, pct_val: float):
        now = datetime.now()
        stamp = now.strftime('%H:%M, %b %d %Y').upper()
        rounded_pct = round(pct_val, 1)

        # create wb notifaction
        ui.notify(f'{metric_name} is over 90% ({rounded_pct}%)!', type='warning', position='top-right')

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
        time_now = time.monotonic()
        for metric_name, val in (('CPU', cpu_pct), ('RAM', ram_pct)):
            # check if value is over 90 pct
            if val > 90.0 and (time_now - last_alert_ts[metric_name]) >= alert_cooldown_sec:
                last_alert_ts[metric_name] = time_now
                alert_system(metric_name, val)

    # update chart
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

        selected = active_filter['metric'] # active filter name
        query = (search_box.value or '').strip().lower()   #<- AAAAAAAAAAAAA->
        data_render = []

        for row in reversed(rows):   # newest first
            _, cpu_raw, ram_raw, _, ts = row
            ts_str = str(ts)

            cpu_d = json.loads(cpu_raw)
            ram_d = json.loads(ram_raw)

            when = ts_str[5:16] if len(ts_str) >= 16 else ts_str 
            row_metrics = [
                ('CPU', cpu_d.get('cpu_percent', 0)),
                ('RAM', ram_d.get('percent', 0)),
            ]

            for label, raw_pct in row_metrics:
                if selected != 'ALL' and selected != label:
                    continue
                # search runs over database
                bigD = f'{ts_str} {label} {round(float(raw_pct), 1)}'.lower()
                if query and query not in bigD:
                    continue
                data_render.append((when, raw_pct, label))

            if len(data_render) >= MAX_HISTORY_ROWS:
                break

        history_container.clear()
        with history_container:
            if not data_render:
                ui.label('No matching history records.').classes('text-xs text-[#98b382] py-2')
                return

            for when, raw_pct, label in data_render[:MAX_HISTORY_ROWS]:
                
                clamped = max(0, min(100, round(float(raw_pct))))

                with ui.row().classes('w-full items-center gap-3 py-2 border-b border-[#2d3528] text-xs'):
                    ui.label(when).classes('text-[#CFEE9E] shrink-0')   #now shows date & time

                    with ui.element('div').classes('flex-1 h-1.5 bg-[#171c14] rounded overflow-hidden'):
                        ui.element('div').classes('h-full bg-[#CFEE9E]').style(f'width: {clamped}%')
                    ui.label(f'{clamped}%').classes('text-[#CFEE9E] w-10 text-right shrink-0') 
                    ui.label(label).classes('font-bold text-[#CFEE9E] w-10 text-right shrink-0')


    # refresh per tick
    async def tick():
        data = await asyncio.to_thread(machine_data)

        cpu_val = float(data['CPU']['cpu_percent'])
        ram_val = float(data['RAM']['percent'])

        set_chart_value(CPU, cpu_val)
        set_chart_value(RAM, ram_val)
        check_high_usage(cpu_val, ram_val)

    refresh_history()
    await tick()       
    ui.timer(REFRESH, tick) 
    ui.timer(60.0, refresh_history)


ui.run_with(
    app, storage_secret="3"
)
