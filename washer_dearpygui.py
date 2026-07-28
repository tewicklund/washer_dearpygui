import dearpygui.dearpygui as dpg
import threading
from funcs import *
import time

# threading event to make stop button work
stop_event=threading.Event()

dpg.create_context()

# port info lists
table_names=["Cold Temp.","Hot Temp.","Cold Pres.","Hot Pres.","Cold Flow","Hot Flow","Near Ambi.","Far Ambi"]
get_unit_functions=[get_cold_temp_unit,get_hot_temp_unit,get_cold_pres_unit,get_hot_pres_unit,get_cold_flow_unit,get_hot_flow_unit,get_temp_rh_near_unit,get_temp_rh_far_unit]
get_value_functions=[get_cold_temp_value,get_hot_temp_value,get_cold_pres_value,get_hot_pres_value,get_cold_flow_value,get_hot_flow_value,get_temp_rh_near_value,get_temp_rh_far_value]
column_headers='sample_num,epoch_timestamp_ms,human_timestamp,'
port_broken_bools=[0,0,0,0,0,0,0,0]

test_duration_samples=10

# adjust vertical sizing for all GUI elements
viewport_width,viewport_height=compute_window_size(960,720)
thin_col_width=0.08*viewport_width
thick_col_width=0.14*viewport_width
middle_col_width=0.04*viewport_width

title_height=viewport_height*0.1
table_height=viewport_height*0.7
button_height=viewport_height*0.2

# adjust font sizes and styles
title_font_height=int(viewport_height*0.05)
header_font_height=int(viewport_height*0.04)
normal_font_height=int(viewport_height*0.030)
button_font_height=int(viewport_height*0.12)
font_styles=["FiraMono-Regular.ttf","DejaVuSans.ttf"]
font_style_choice=font_styles[1]

table_row_height=0.15*table_height
table_text_pad_v=(table_row_height-normal_font_height)/2


# START button callback function
def start_test():

    # clear the stop event in case the last session was stopped 
    stop_event.clear()

    # start main test script in another thread, allowing GUI updates and button presses while main script runs
    threading.Thread(target=worker, daemon=True).start()

# stop test callback function
def stop_test():
    stop_event.set()
    dpg.set_value('status_text','Stopped')
    for port_num in range(8):
        dpg.set_value(f'X{port_num}_value','*****')
        dpg.set_value(f'X{port_num}_unit','*****')
        dpg.bind_item_theme(f'X{port_num}_unit',washer_theme)
        dpg.bind_item_theme(f'X{port_num}_value',washer_theme)
        dpg.bind_item_theme(f'X{port_num}_port',washer_theme)
        dpg.bind_item_theme(f'X{port_num}_name',washer_theme)

# function containing main test loop that can exit when STOP is pressed
def worker():
    dpg.set_value('status_text','Starting')
    test_duration_samples=int(dpg.get_value('test_duration_seconds'))

    # try to set units for flow sensor to gallons per minute
    if not set_flow_units_gpm():
        print("One or more flow sensors could not be configured.")

    # set up column headers in the log file and UI
    with open('dummy_log.csv','w') as dummy_file:
        dummy_file.write('sample_num,epoch_timestamp_ms,human_timestamp,')
        for port_num in range(8):
            requested_unit=get_unit_functions[port_num]()
            if requested_unit=='offline':
                requested_unit='???'
                port_broken_bools[port_num]=1
                dpg.bind_item_theme(f'X{port_num}_unit',red_theme)
                dpg.bind_item_theme(f'X{port_num}_value',red_theme)
                dpg.bind_item_theme(f'X{port_num}_port',red_theme)
                dpg.bind_item_theme(f'X{port_num}_name',red_theme)
            dummy_file.write(f'{table_names[port_num]} ({requested_unit}),')
            dpg.set_value(f"X{port_num}_unit",requested_unit)
        dummy_file.write('\n')

        
    # main test loop
    x=0
    indefinite_logging=False
    if test_duration_samples<=0:
        indefinite_logging=True
    while not stop_event.is_set() and (x<test_duration_samples or indefinite_logging):
        x+=1
        dpg.set_value('status_text',f'Sample {x}')
        print(f'Collecting data point {x}')
        timestamp_data=make_timestamp(x)
        prev_ts=time.time()
        with open('dummy_log.csv','a') as dummy_file:
            dummy_file.write(f" {timestamp_data['sample_num']} , {timestamp_data['epoch_timestamp_ms']} , {timestamp_data['human_timestamp']},")

            for port_num in range(8):
                requested_value=get_value_functions[port_num]()
                dummy_file.write(f'{requested_value},')
                dpg.set_value(f"X{port_num}_value",requested_value)
            dummy_file.write('\n')
            
            

        if (time.time()-prev_ts>1):
            print("WARNING: POLLING RATE IS TOO FAST")
        while (time.time()-prev_ts<1):
            pass

    # wrap up after test loop is done, reset UI
    dpg.set_value('status_text','Finishing')
    for port_num in range(8):
            dpg.set_value(f'X{port_num}_value','*****')
            dpg.set_value(f'X{port_num}_unit','*****')
            dpg.bind_item_theme(f'X{port_num}_unit',washer_theme)
            dpg.bind_item_theme(f'X{port_num}_value',washer_theme)
            dpg.bind_item_theme(f'X{port_num}_port',washer_theme)
            dpg.bind_item_theme(f'X{port_num}_name',washer_theme)
    dpg.set_value('status_text','Ready')






# add a font registry, needed for having next of different sizes
with dpg.font_registry():
    #first argument ids the path to the .ttf or .otf file
    title_font = dpg.add_font(font_style_choice, title_font_height)
    header_font = dpg.add_font(font_style_choice, header_font_height)
    normal_font = dpg.add_font(font_style_choice, normal_font_height)
    button_font=dpg.add_font(font_style_choice, button_font_height)

with dpg.theme() as red_theme:
    with dpg.theme_component(dpg.mvText):
        dpg.add_theme_color(dpg.mvThemeCol_Text,(255,80,80,255))
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, viewport_width*0.025, viewport_height*0.02)
        dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
    
# add themes to adjust padding
with dpg.theme() as washer_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, viewport_width*0.025, viewport_height*0.02)
        dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)

# text defaults to normal font
dpg.bind_font(normal_font)

# window at the top with the title
with dpg.window( pos=(0,0),width=viewport_width,height=title_height,no_move=True,no_resize=True,no_title_bar=True,tag="title_window"):
    dpg.add_text("IO-Link Hub Laundry M&V Viewer and Logger V1.0",tag='title_text')
    dpg.bind_item_font('title_text',title_font)
dpg.bind_item_theme("title_window",washer_theme)


# middle window with the big feedback table
with dpg.window( pos=(0,title_height),width=viewport_width,height=table_height,no_move=True,no_resize=True,no_title_bar=True,tag="table_window"):
    
    with dpg.table(header_row=False,borders_innerH=True,borders_innerV=False):
        
        dpg.add_table_column(width_fixed=True, init_width_or_weight=thin_col_width)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=thick_col_width)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=thin_col_width)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=thin_col_width)

        dpg.add_table_column(width_fixed=True, init_width_or_weight=middle_col_width)

        dpg.add_table_column(width_fixed=True, init_width_or_weight=thin_col_width)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=thick_col_width)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=thin_col_width)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=thin_col_width)


        with dpg.table_row(height = table_height * 0.1):

            dpg.add_text("Port",    tag='h0')
            dpg.add_text("Name",    tag='h1')
            dpg.add_text("Value",   tag='h2')
            dpg.add_text("Unit",    tag='h3')

            dpg.add_text("   ")
            
            dpg.add_text("Port",    tag='h4')
            dpg.add_text("Name",    tag='h5')
            dpg.add_text("Value",   tag='h6')
            dpg.add_text("Unit",    tag='h7')

            for _ in range(8):
                dpg.bind_item_font(f'h{_}',header_font)

        
         
        for row_num in range(4):
            with dpg.table_row(height=table_row_height,):
                entry_number=3-row_num
                with dpg.group():
                    dpg.add_spacer(height=table_text_pad_v)
                    dpg.add_text(f'X{str(entry_number)}',tag=f'X{str(entry_number)}_port')
                with dpg.group():
                    dpg.add_spacer(height=table_text_pad_v)
                    dpg.add_text(table_names[entry_number],tag=f'X{str(entry_number)}_name')
                with dpg.group():
                    dpg.add_spacer(height=table_text_pad_v)
                    dpg.add_text("*****",tag=f'X{str(entry_number)}_value')
                with dpg.group():
                    dpg.add_spacer(height=table_text_pad_v)
                    dpg.add_text("*****",tag=f'X{str(entry_number)}_unit')

                dpg.add_text("   ")

                entry_number=7-row_num
                with dpg.group():
                    dpg.add_spacer(height=table_text_pad_v)
                    dpg.add_text(f'X{str(entry_number)}',tag=f'X{str(entry_number)}_port')
                with dpg.group():
                    dpg.add_spacer(height=table_text_pad_v)
                    dpg.add_text(table_names[entry_number],tag=f'X{str(entry_number)}_name')
                with dpg.group():
                    dpg.add_spacer(height=table_text_pad_v)
                    dpg.add_text("*****",tag=f'X{str(entry_number)}_value')
                with dpg.group():
                    dpg.add_spacer(height=table_text_pad_v)
                    dpg.add_text("*****",tag=f'X{str(entry_number)}_unit')

        with dpg.table_row(height=table_row_height/2):
            pass
        with dpg.table_row(height=table_row_height,):
            with dpg.group():
                dpg.add_spacer(height=table_text_pad_v)
                dpg.add_text('Status:')
            with dpg.group():
                dpg.add_spacer(height=table_text_pad_v)
                dpg.add_text('Ready',tag='status_text')
            with dpg.group():
                dpg.add_spacer(height=table_text_pad_v)
                dpg.add_text('     ')
            with dpg.group():
                dpg.add_spacer(height=table_text_pad_v)
                dpg.add_text('     ')
            with dpg.group():
                dpg.add_spacer(height=table_text_pad_v)
                dpg.add_text     
            with dpg.group():
                dpg.add_spacer(height=table_text_pad_v)
                dpg.add_text('Time:')
            with dpg.group():
                dpg.add_spacer(height=table_text_pad_v)
                dpg.add_input_text(default_value='10',tag='test_duration_seconds')
            with dpg.group():
                dpg.add_spacer(height=table_text_pad_v)
                dpg.add_text('s')
                
            

dpg.bind_item_theme("table_window",washer_theme)


# seperate window at bottom for start and stop buttons
with dpg.window( pos=(0,title_height+table_height),width=viewport_width,height=button_height,no_move=True,no_resize=True,no_title_bar=True,tag='button_window'):

    with dpg.table(header_row=False,borders_innerH=True):

        dpg.add_table_column()
        dpg.add_table_column()

        with dpg.table_row():

            decrement_button=dpg.add_button(label="     START    ",callback=start_test)
            increment_button=dpg.add_button(label="     STOP     ",callback=stop_test)
            dpg.bind_item_font(decrement_button,button_font)
            dpg.bind_item_font(increment_button,button_font)
            
dpg.bind_item_theme("button_window",washer_theme)


# start GUI and destroy when closed
dpg.create_viewport(title='Washer M&V GUI', width=viewport_width, height=viewport_height,resizable=False)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()