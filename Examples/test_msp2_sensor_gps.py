import time
import datetime
import struct

from yamspy import MSPy, msp_ctrl

# $ python -m yamspy.msp_proxy --ports 54310 54320 54330 54340
serial_port = 54320
FC_SEND_LOOP_TIME = 1/10

msp2_gps_format = '<BHIBBHHHHiiiiiiHHHBBBBB' # https://docs.python.org/3/library/struct.html#format-characters
gps_template = {
             'instance': 0,                  # uint8 -  sensor instance number to support multi-sensor setups
             'gpsWeek':  0,                  # uint16 - GPS week, 0xFFFF if not available
             'msTOW': 0,                     # uint32
             'fixType': 0,                   # uint8
             'satellitesInView': 0,          # uint8
             'horizontalPosAccuracy': 0,      # uint16 - [cm]
             'verticalPosAccuracy': 0,        # uint16 - [cm]
             'horizontalVelAccuracy': 0,      # uint16 - [cm/s]
             'hdop': 0,                       # uint16
             'longitude': 0,                  # int32
             'latitude': 0,                   # int32
             'mslAltitude': 0,                # int32 - [cm]
             'nedVelNorth': 0,                # int32 - [cm/s]
             'nedVelEast': 0,                 # int32
             'nedVelDown': 0,                 # int32
             'groundCourse': 0,               # uint16 - deg * 100, 0..36000
             'trueYaw': 0,                    # uint16 - deg * 100, values of 0..36000 are valid. 65535 = no data available
             'year': 0,                       # uint16
             'month': 0,                      # uint8
             'day': 0,                        # uint8
             'hour': 0,                       # uint8
             'min': 0,                        # uint8
             'sec': 0,                        # uint8
}



with MSPy(device=serial_port, loglevel='WARNING', baudrate=115200, use_tcp=True) as board:
    command_list = ['MSP_API_VERSION', 'MSP_FC_VARIANT', 'MSP_FC_VERSION', 'MSP_BUILD_INFO',
                    'MSP_BOARD_INFO', 'MSP_UID', 'MSP_ACC_TRIM', 'MSP_NAME', 'MSP_STATUS',
                    'MSP_STATUS_EX','MSP_BATTERY_CONFIG', 'MSP_BATTERY_STATE', 'MSP_BOXNAMES']
    for msg in command_list:
        if board.send_RAW_msg(MSPy.MSPCodes[msg], data=[]):
            dataHandler = board.receive_msg()
            board.process_recv_data(dataHandler)
    try:
        mspSensorGpsDataMessage = gps_template.copy()
        mspSensorGpsDataMessage['instance'] = 1
        mspSensorGpsDataMessage['fixType'] = 10
        mspSensorGpsDataMessage['satellitesInView'] = mspSensorGpsDataMessage['fixType']
        mspSensorGpsDataMessage['gpsWeek'] = 0xFFFF

        ############ SEND GPS DATA #############
        # gpsSol.llh.lon   = pkt->longitude;
        mspSensorGpsDataMessage['longitude'] = -73.61319383049725 * 10000000
        # gpsSol.llh.lat   = pkt->latitude;
        mspSensorGpsDataMessage['latitude'] = 45.50496682273918 * 10000000
        # gpsSol.llh.alt   = pkt->mslAltitude;
        mspSensorGpsDataMessage['mslAltitude'] = 5000 # [cm]
        # gpsSol.velNED[X] = pkt->nedVelNorth;
        mspSensorGpsDataMessage['nedVelNorth'] = 0
        # gpsSol.velNED[Y] = pkt->nedVelEast;
        mspSensorGpsDataMessage['nedVelEast'] = 0
        # gpsSol.velNED[Z] = pkt->nedVelDown;
        mspSensorGpsDataMessage['nedVelDown'] = 0
        # gpsSol.groundSpeed = calc_length_pythagorean_2D((float)pkt->nedVelNorth, (float)pkt->nedVelEast);
        # gpsSol.groundCourse = pkt->groundCourse / 10;   // in deg * 10
        mspSensorGpsDataMessage['groundCourse'] = 0
        # gpsSol.eph = gpsConstrainEPE(pkt->horizontalPosAccuracy / 10);
        mspSensorGpsDataMessage['horizontalPosAccuracy'] = 10
        # gpsSol.epv = gpsConstrainEPE(pkt->verticalPosAccuracy / 10);
        mspSensorGpsDataMessage['verticalPosAccuracy'] = 10
        # gpsSol.hdop = gpsConstrainHDOP(pkt->hdop);
        mspSensorGpsDataMessage['hdop'] = 100
        # gpsSol.time.year   = pkt->year;
        # mspSensorGpsDataMessage['year'] = 2022
        # # gpsSol.time.month  = pkt->month;
        # mspSensorGpsDataMessage['month'] = 1
        # # gpsSol.time.day    = pkt->day;
        # mspSensorGpsDataMessage['day'] = 2
        # # gpsSol.time.hours  = pkt->hour;
        # mspSensorGpsDataMessage['hour'] = 3
        # # gpsSol.time.minutes = pkt->min;
        # mspSensorGpsDataMessage['min'] = 4
        # # gpsSol.time.seconds = pkt->sec;
        # mspSensorGpsDataMessage['sec'] = 5
        
        while True:
            now = datetime.datetime.now()
            print(now)
            mspSensorGpsDataMessage['year'] = now.year
            mspSensorGpsDataMessage['month'] = now.month
            mspSensorGpsDataMessage['day'] = now.day
            mspSensorGpsDataMessage['hour'] = now.hour
            mspSensorGpsDataMessage['min'] = now.minute
            mspSensorGpsDataMessage['sec'] = now.second
            gps_data = struct.pack(msp2_gps_format, *[int(i) for i in mspSensorGpsDataMessage.values()])

            # Ask GPS data
            if board.send_RAW_msg(MSPy.MSPCodes['MSP_RAW_GPS'], data=[]):
                print("MSP_RAW_GPS data sent!")
                dataHandler = board.receive_msg()
                print("MSP_RAW_GPS ACK data received!")
                board.process_recv_data(dataHandler)
                print("MSP_RAW_GPS data processed!")
            else:
                print("MSP_RAW_GPS not sent!")

            # Received GPS data
            print(board.GPS_DATA)

            # Send GPS data
            if board.send_RAW_msg(MSPy.MSPCodes['MSP2_SENSOR_GPS'], data=gps_data):
                print(f"MSP2_SENSOR_GPS data {gps_data} sent!")
            else:
                print("MSP2_SENSOR_GPS not sent!")

            time.sleep(FC_SEND_LOOP_TIME)

    except KeyboardInterrupt:
        print("stop")
    finally:
        pass
        #board.reboot()