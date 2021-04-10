import streamlit as st
import pandas as pd
from socket import gethostname
import config
import sqlite3
from sqlite3 import Connection
import logging
from detections import get_motion_df, get_object_det_df
from security import find_owners_at_home
from database import get_db_conn


def main():
    """
    Main contains whole app execution, when page is reloaded of buttons are
    clicked, Streamlit will re-run the main from top to bottom
    """

    @st.cache(hash_funcs={Connection: id})
    def get_connection() -> Connection:
        """Create a DB Connection"""
        return get_db_conn()

    @st.cache(hash_funcs={sqlite3.Connection: id}, ttl=config.DETECTIONS_DATA_CACHE_TTL)
    def get_motion_data(db_conn: Connection) -> pd.DataFrame:
        """Create dataframe with motion detections"""
        return get_motion_df(db_conn)

    @st.cache(hash_funcs={sqlite3.Connection: id}, ttl=config.DETECTIONS_DATA_CACHE_TTL)
    def get_object_det_data(db_conn: Connection) -> dict:
        """Create dataframe with object detections"""
        return get_object_det_df(db_conn)

    @st.cache(hash_funcs={sqlite3.Connection: id}, ttl=config.OCCUPANCY_DATA_CACHE_TTL)
    def get_home_status_data(db_conn: Connection) -> list:
        """Get a list of users currently occupying the house"""
        return find_owners_at_home(db_conn)

    # Show home occupancy status: home or away (in the side bar)
    if config.SHOW_HOME_OCCUPANCY_STATUS:
        conn = get_connection()
        home_owners = get_home_status_data(conn)
        st.sidebar.subheader('Home occupancy status:')
        st.sidebar.text(f'At home: {", ".join(home_owners)}' if len(home_owners) > 0 else 'Away')

    # Enable side panel and add checkboxes to configure view
    st.sidebar.subheader('Configure view:')
    show_video_checkbox = st.sidebar.checkbox("Live Video Stream", True)
    motion_analysis_checkbox = st.sidebar.checkbox("Motion Analysis", False)
    object_analysis_checkbox = st.sidebar.checkbox("Objects Analysis", False)

    # Set up top headers
    st.title(config.APP_NAME)
    st.subheader('AI-powered Web App for Home Monitoring')
    html_string = "<hr style='margin: 10px 0 15px 0;'>"
    st.markdown(html_string, unsafe_allow_html=True)

    # Show video stream
    if show_video_checkbox:
        st.markdown("""#### Live Video Stream""")
        st.image(config.VIDEO_STREAM_URL, use_column_width='auto', caption=f'Device: {gethostname()}')

    # Show motion analysis visualisations
    if motion_analysis_checkbox:
        st.markdown(f"""#### Motion Analysis - today vs {config.USE_HISTORICAL_DAYS - 1}-days average""")
        conn = get_connection()
        motion_data = get_motion_data(conn)
        st.area_chart(motion_data)
        st.button('Refresh Data', key='refresh-motion-det')

    # Show object detection analysis visualisations
    if object_analysis_checkbox:
        st.markdown(f"""#### Object Analysis - today vs {config.USE_HISTORICAL_DAYS - 1}-days average""")
        st.markdown('<div style="margin-top: 5px;"></div>', unsafe_allow_html=True)
        conn = get_connection()
        object_det_data = get_object_det_data(conn)
        checkboxes = {}
        for label in config.TRACK_OBJECTS:
            checkboxes[label] = st.checkbox(label.capitalize(), False)
            if checkboxes[label]:
                st.area_chart(object_det_data[label])
        st.button('Refresh Data', key='refresh-object-det')


if __name__ == "__main__":
    logging.basicConfig(format=config.LOGGING_FORMAT, level=config.LOGGING_LEVEL, datefmt="%H:%M:%S")
    main()
