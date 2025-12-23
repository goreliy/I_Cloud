"""Data processing service for aggregation and statistics"""
from typing import List, Optional
from datetime import datetime, timedelta
from statistics import median as stat_median
from collections import defaultdict

from app.models.feed import Feed


def timescale_data(feeds: List[Feed], minutes: int) -> List[dict]:
    """
    Aggregate feed data by time intervals
    Groups entries into time buckets and averages the values
    """
    if not feeds or minutes <= 0:
        return []
    
    # Group feeds by time buckets
    buckets = defaultdict(lambda: {
        'count': 0,
        'field1': [], 'field2': [], 'field3': [], 'field4': [],
        'field5': [], 'field6': [], 'field7': [], 'field8': [],
        'created_at': None
    })
    
    for feed in feeds:
        # Calculate bucket timestamp
        timestamp = feed.created_at
        bucket_time = timestamp - timedelta(
            minutes=timestamp.minute % minutes,
            seconds=timestamp.second,
            microseconds=timestamp.microsecond
        )
        bucket_key = bucket_time.isoformat()
        
        bucket = buckets[bucket_key]
        bucket['count'] += 1
        bucket['created_at'] = bucket_time
        
        # Add field values
        for i in range(1, 9):
            field_name = f'field{i}'
            value = getattr(feed, field_name)
            if value is not None:
                bucket[field_name].append(value)
    
    # Calculate averages
    result = []
    for bucket_key, bucket in sorted(buckets.items()):
        entry = {
            'created_at': bucket['created_at'],
            'entry_count': bucket['count']
        }
        for i in range(1, 9):
            field_name = f'field{i}'
            values = bucket[field_name]
            if values:
                entry[field_name] = sum(values) / len(values)
            else:
                entry[field_name] = None
        result.append(entry)
    
    return result


def calculate_average(feeds: List[Feed], minutes: Optional[int] = None) -> List[dict]:
    """
    Calculate average values for feed data
    If minutes is specified, groups by time intervals
    """
    if minutes:
        return timescale_data(feeds, minutes)
    
    # Calculate overall average
    if not feeds:
        return []
    
    averages = {'entry_count': len(feeds)}
    
    for i in range(1, 9):
        field_name = f'field{i}'
        values = [getattr(f, field_name) for f in feeds if getattr(f, field_name) is not None]
        if values:
            averages[field_name] = sum(values) / len(values)
        else:
            averages[field_name] = None
    
    return [averages]


def calculate_median(feeds: List[Feed], field_num: Optional[int] = None) -> List[dict]:
    """
    Calculate median values for feed data
    If field_num is specified, calculates for that field only
    """
    if not feeds:
        return []
    
    result = {'entry_count': len(feeds)}
    
    if field_num:
        field_name = f'field{field_num}'
        values = [getattr(f, field_name) for f in feeds if getattr(f, field_name) is not None]
        if values:
            result[field_name] = stat_median(values)
        else:
            result[field_name] = None
    else:
        for i in range(1, 9):
            field_name = f'field{i}'
            values = [getattr(f, field_name) for f in feeds if getattr(f, field_name) is not None]
            if values:
                result[field_name] = stat_median(values)
            else:
                result[field_name] = None
    
    return [result]


def calculate_sum(feeds: List[Feed], minutes: Optional[int] = None) -> List[dict]:
    """
    Calculate sum of values for feed data
    If minutes is specified, groups by time intervals
    """
    if minutes:
        # Group by time and sum
        buckets = defaultdict(lambda: {
            'count': 0,
            'field1': 0, 'field2': 0, 'field3': 0, 'field4': 0,
            'field5': 0, 'field6': 0, 'field7': 0, 'field8': 0,
            'created_at': None
        })
        
        for feed in feeds:
            timestamp = feed.created_at
            bucket_time = timestamp - timedelta(
                minutes=timestamp.minute % minutes,
                seconds=timestamp.second,
                microseconds=timestamp.microsecond
            )
            bucket_key = bucket_time.isoformat()
            
            bucket = buckets[bucket_key]
            bucket['count'] += 1
            bucket['created_at'] = bucket_time
            
            for i in range(1, 9):
                field_name = f'field{i}'
                value = getattr(feed, field_name)
                if value is not None:
                    bucket[field_name] += value
        
        return [dict(bucket) for bucket in sorted(buckets.values(), key=lambda x: x['created_at'])]
    
    # Calculate overall sum
    if not feeds:
        return []
    
    sums = {'entry_count': len(feeds)}
    
    for i in range(1, 9):
        field_name = f'field{i}'
        values = [getattr(f, field_name) for f in feeds if getattr(f, field_name) is not None]
        if values:
            sums[field_name] = sum(values)
        else:
            sums[field_name] = None
    
    return [sums]


def round_values(feeds: List[Feed], decimals: int) -> List[Feed]:
    """
    Round field values to specified number of decimal places
    Returns modified feed objects (in memory only, not saved to DB)
    """
    for feed in feeds:
        for i in range(1, 9):
            field_name = f'field{i}'
            value = getattr(feed, field_name)
            if value is not None:
                setattr(feed, field_name, round(value, decimals))
    
    return feeds

