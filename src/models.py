from sqlalchemy import Column, Integer, String, DateTime, Float, JSON
from database import Base, engine
import re
import json


class Command(Base):
    __tablename__ = "command"
    id = Column(Integer, primary_key=True, index=True)
    create_ts = Column(DateTime, unique=False, index=True, nullable=False)
    command_type = Column(String(25), unique=False, index=False, nullable=False)
    command = Column(String(255), unique=False, index=False, nullable=False)
    raw_body = Column(String(255), nullable=False)
    parsed_body = Column(JSON, nullable=True)

    def __init__(self, *args, **kwargs):
        """
        Overwrite constructor and parse raw body to dict
        """
        super().__init__(*args, **kwargs)
        self.parsed_body = self.parse_body()

    def parse_body(self):
        """Find dict formatted string in the body and try to parse it"""
        results = re.search(r'({.+})', self.raw_body)
        if results is not None:
            first_match = results.groups()[0]
            return json.loads(first_match)
        return None


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), unique=False, index=False, nullable=False)
    alert_status = Column(String(25), unique=False, index=False, nullable=False)
    create_ts = Column(DateTime, unique=False, index=True, nullable=False)
    update_ts = Column(DateTime, unique=False, index=True, nullable=True)
    alert_metadata = Column(JSON, nullable=True)


class HomeOccupancy(Base):
    __tablename__ = "home_occupancy"
    id = Column(Integer, primary_key=True, index=True)
    create_ts = Column(DateTime, unique=False, index=True, nullable=False)
    update_ts = Column(DateTime, unique=False, index=True, nullable=True)
    occupancy_status = Column(String(10), unique=False, index=False, nullable=False)
    found_owners = Column(JSON, nullable=True)


class Detection(Base):
    """Base (abstract) class for detections"""
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)
    create_ts = Column(DateTime, unique=False, index=True, nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    w = Column(Integer, nullable=False)
    h = Column(Integer, nullable=False)
    area = Column(Integer, nullable=False)  # contour or bounding box area


# (datetime.now(), (x, y, w, h), cv2.contourArea(cnt))
class MotionDetection(Detection):
    __tablename__ = "motion_detections"


# (datetime.now(), obj_category, (x, y, w, h), w*h)  # bounding box area
class ObjectDetection(Detection):
    __tablename__ = "object_detections"
    label = Column(String(125), unique=False, index=False, nullable=False)
    obj_id = Column(Integer, nullable=False)
    score = Column(Float(10), nullable=True)

    def __init__(self, *args, **kwargs):
        """
        Overwrite constructor and calculate centroids in instances:
        cx, cy = (x+w) / 2, (y+h) / 2
        """
        super().__init__(*args, **kwargs)
        self.cx = int((self.x + self.w) / 2)
        self.cy = int((self.y + self.h) / 2)


# create DB schema if this script is called directly
if __name__ == "__main__":
    Base.metadata.create_all(engine)
