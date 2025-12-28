# City-Scale Waste Collection Route Optimization

## Project Overview
Urban waste collection is a complex logistics problem involving hundreds of collection points, limited vehicle capacities, fixed working hours, and real-world road constraints. Inefficient routing leads to increased fuel consumption, delayed pickups, and higher operational costs.

This project implements a real-world, scalable routing optimization system for municipal waste collection using Google OR-Tools, OpenStreetMap road networks, and machine learning-based clustering. The system is designed to work on actual city data and respects capacity limits, shift duration, time windows, and real road travel times.

---

## Problem Statement
Municipal authorities must collect waste from multiple Garbage Vulnerable Points (GVPs) and transport it to designated Secondary Collection and Transfer Points (SCTPs) using a limited fleet of vehicles.

The objective is to minimize total travel time while satisfying operational constraints such as:
- Vehicle capacity limits  
- Fixed driver working hours (shift duration)  
- Time-restricted waste pickup windows  
- Real-world road network constraints  
- Multiple vehicles and depots  

---

## Features
- K-Means clustering to divide the city into manageable zones  
- Automatic assignment of the nearest SCTP to each cluster  
- Multiple vehicles per cluster  
- Vehicle capacity constraints  
- Shift duration (working hours) enforcement  
- Time windows at waste collection points  
- Real road travel time using OpenStreetMap (OSM)  
- Vehicle Routing Problem with Time Windows (VRPTW) using Google OR-Tools  

---

## Technology Stack
- Python  
- Google OR-Tools  
- OSMnx & NetworkX  
- Scikit-learn  
- NumPy  

---

## How to Run
1. Install dependencies:
```bash
pip install -r requirements.txt
