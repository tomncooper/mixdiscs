""" Unit tests for validation.py """

import pytest
from datetime import timedelta
from pathlib import Path

from mixdiscer.validation import (
    ValidationResult,
    format_validation_results,
    format_duration,
)


def test_validation_result_duration_exceeded():
    """Test that duration_exceeded property works correctly"""
    result_valid = ValidationResult(
        filepath=Path("test.yaml"),
        user="TestUser",
        title="Test",
        is_valid=True,
        total_duration=timedelta(minutes=70),
        duration_threshold=timedelta(minutes=80),
        missing_tracks=[]
    )
    
    result_exceeded = ValidationResult(
        filepath=Path("test.yaml"),
        user="TestUser",
        title="Test",
        is_valid=False,
        total_duration=timedelta(minutes=90),
        duration_threshold=timedelta(minutes=80),
        missing_tracks=[]
    )
    
    assert not result_valid.duration_exceeded
    assert result_exceeded.duration_exceeded


def test_validation_result_duration_difference():
    """Test duration_difference calculation"""
    result = ValidationResult(
        filepath=Path("test.yaml"),
        user="TestUser",
        title="Test",
        is_valid=False,
        total_duration=timedelta(minutes=90),
        duration_threshold=timedelta(minutes=80),
        missing_tracks=[]
    )
    
    assert result.duration_difference == timedelta(minutes=10)


def test_validation_result_duration_difference_under_threshold():
    """Test duration_difference when under threshold"""
    result = ValidationResult(
        filepath=Path("test.yaml"),
        user="TestUser",
        title="Test",
        is_valid=True,
        total_duration=timedelta(minutes=70),
        duration_threshold=timedelta(minutes=80),
        missing_tracks=[]
    )
    
    # Difference is negative when under
    assert result.duration_difference == timedelta(minutes=-10)


def test_format_validation_results_all_pass():
    """Test formatting when all playlists pass"""
    results = [
        ValidationResult(
            filepath=Path("test1.yaml"),
            user="User1",
            title="Playlist 1",
            is_valid=True,
            total_duration=timedelta(minutes=70),
            duration_threshold=timedelta(minutes=80),
            missing_tracks=[]
        ),
        ValidationResult(
            filepath=Path("test2.yaml"),
            user="User2",
            title="Playlist 2",
            is_valid=True,
            total_duration=timedelta(minutes=60),
            duration_threshold=timedelta(minutes=80),
            missing_tracks=[]
        ),
    ]
    
    output = format_validation_results(results)
    
    assert "✅ All 2 playlist(s) passed validation!" in output
    assert "Playlist 1" in output
    assert "Playlist 2" in output
    assert "70:00" in output
    assert "60:00" in output


def test_format_validation_results_all_fail():
    """Test formatting when all playlists fail"""
    results = [
        ValidationResult(
            filepath=Path("test1.yaml"),
            user="User1",
            title="Playlist 1",
            is_valid=False,
            total_duration=timedelta(minutes=90),
            duration_threshold=timedelta(minutes=80),
            missing_tracks=[]
        ),
        ValidationResult(
            filepath=Path("test2.yaml"),
            user="User2",
            title="Playlist 2",
            is_valid=False,
            total_duration=timedelta(minutes=85),
            duration_threshold=timedelta(minutes=80),
            missing_tracks=[]
        ),
    ]
    
    output = format_validation_results(results)
    
    assert "❌ 2 of 2 playlist(s) failed validation" in output
    assert "Failed Playlists" in output
    assert "Playlist 1" in output
    assert "Playlist 2" in output


def test_format_validation_results_mixed():
    """Test formatting with mix of pass and fail"""
    results = [
        ValidationResult(
            filepath=Path("pass.yaml"),
            user="User1",
            title="Pass Playlist",
            is_valid=True,
            total_duration=timedelta(minutes=70),
            duration_threshold=timedelta(minutes=80),
            missing_tracks=[]
        ),
        ValidationResult(
            filepath=Path("fail.yaml"),
            user="User2",
            title="Fail Playlist",
            is_valid=False,
            total_duration=timedelta(minutes=90),
            duration_threshold=timedelta(minutes=80),
            missing_tracks=[]
        ),
    ]
    
    output = format_validation_results(results)
    
    assert "❌ 1 of 2 playlist(s) failed validation" in output
    assert "Failed Playlists" in output
    assert "Passed Playlists" in output
    assert "Pass Playlist" in output
    assert "Fail Playlist" in output


def test_format_validation_results_with_error_message():
    """Test formatting when result has error message"""
    results = [
        ValidationResult(
            filepath=Path("error.yaml"),
            user="TestUser",
            title="Error Playlist",
            is_valid=False,
            total_duration=timedelta(),
            duration_threshold=timedelta(minutes=80),
            missing_tracks=[],
            error_message="Failed to load playlist file"
        ),
    ]
    
    output = format_validation_results(results)
    
    assert "Error Playlist" in output
    assert "Failed to load playlist file" in output


def test_format_validation_results_with_duplicates():
    """Test formatting when playlist is duplicate"""
    results = [
        ValidationResult(
            filepath=Path("duplicate.yaml"),
            user="TestUser",
            title="Duplicate Playlist",
            is_valid=False,
            total_duration=timedelta(),
            duration_threshold=timedelta(minutes=80),
            missing_tracks=[],
            duplicate_of=Path("original.yaml")
        ),
    ]
    
    output = format_validation_results(results)
    
    assert "Duplicate Playlist" in output
    assert "Duplicate:" in output
    assert "original.yaml" in output
    assert "globally unique" in output


def test_format_validation_results_with_missing_tracks():
    """Test formatting with missing tracks"""
    results = [
        ValidationResult(
            filepath=Path("test.yaml"),
            user="TestUser",
            title="Test Playlist",
            is_valid=True,
            total_duration=timedelta(minutes=70),
            duration_threshold=timedelta(minutes=80),
            missing_tracks=[
                ("Artist1", "Song1"),
                ("Artist2", "Song2"),
            ]
        ),
    ]
    
    output = format_validation_results(results)
    
    assert "Test Playlist" in output
    assert "2 track(s) not found" in output


def test_format_validation_results_empty():
    """Test formatting with no results"""
    output = format_validation_results([])
    
    assert "No playlists to validate" in output


def test_format_validation_results_exceeded_duration_details():
    """Test that exceeded duration shows details"""
    results = [
        ValidationResult(
            filepath=Path("test.yaml"),
            user="TestUser",
            title="Long Playlist",
            is_valid=False,
            total_duration=timedelta(minutes=90, seconds=30),
            duration_threshold=timedelta(minutes=80),
            missing_tracks=[]
        ),
    ]
    
    output = format_validation_results(results)
    
    assert "Long Playlist" in output
    assert "90:30" in output
    assert "exceeds limit by 10:30" in output


def test_format_duration():
    """Test duration formatting"""
    assert format_duration(timedelta(minutes=3, seconds=45)) == "3:45"
    assert format_duration(timedelta(minutes=70, seconds=5)) == "70:05"
    assert format_duration(timedelta(hours=1, minutes=20, seconds=30)) == "80:30"
    assert format_duration(timedelta(seconds=45)) == "0:45"
    assert format_duration(timedelta(minutes=0, seconds=5)) == "0:05"


def test_format_duration_zero():
    """Test formatting zero duration"""
    assert format_duration(timedelta()) == "0:00"


def test_format_duration_large():
    """Test formatting large duration"""
    # 2 hours = 120 minutes
    assert format_duration(timedelta(hours=2, minutes=15, seconds=30)) == "135:30"
