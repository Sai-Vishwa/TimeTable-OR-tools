import json
from ortools.sat.python import cp_model
from collections import defaultdict
import time
import logging
import os
import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate

# ----------------------------
# LOGGER SETUP
# ----------------------------
def setup_logger():
    """Configure logging with timestamps and file output"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    logger = logging.getLogger('timetable_optimizer')
    logger.setLevel(logging.DEBUG)
    
    # File handler
    fh = logging.FileHandler(f'logs/timetable_{time.strftime("%Y%m%d_%H%M%S")}.log')
    fh.setLevel(logging.DEBUG)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

logger = setup_logger()

# ----------------------------
# DATA LOADING & PREPROCESSING
# ----------------------------
def load_data():
    """Load and process input data with timing"""
    logger.info(" Loading data files...")
    start_time = time.perf_counter()
    try:
        with open('final.json') as f:
            dept_sem_data = json.load(f)
        with open('lab_course_mapping.json') as f:
            lab_course_mapping = json.load(f)
    except Exception as e:
        logger.error(f" Error loading files: {e}")
        raise

    # Create reverse lab mapping: course -> lab rooms
    course_lab_map = {}
    for lab, courses in lab_course_mapping.items():
        for course in courses:
            course_lab_map[course] = course_lab_map.get(course, []) + [lab]
    
    load_time = time.perf_counter() - start_time
    logger.info(f" Data loaded successfully in {load_time:.2f}s")
    logger.info(f"  - Departments: {len(dept_sem_data)}")
    logger.info(f"  - Lab mappings: {len(course_lab_map)} courses mapped")
    return dept_sem_data, course_lab_map

def create_activities(dept_sem_data, course_lab_map):
    """Generate scheduling activities and track requirements with timing"""
    logger.info("\n Creating scheduling activities...")
    start_time = time.perf_counter()
    activities = []
    allocation_status = {}
    course_group_map = defaultdict(list)
    activity_id = 0

    for dept, sem_data in dept_sem_data.items():
        for sem, courses in sem_data.items():
            for course, staff_list in courses.items():
                # Get requirements
                theory_hours = staff_list[0]['lecture_hours']
                lab_hours = staff_list[0]['practical_hours']
                
                # Initialize tracking
                key = (dept, sem, course)
                allocation_status.setdefault(key, {
                    'theory': {'allocated': 0, 'required': (theory_hours+1) // 2},
                    'lab': {'allocated': 0, 'required': lab_hours}
                })
                
                # Create theory sessions
                for session in range((theory_hours+1) // 2):
                    activity_id_str = f"A{activity_id}"
                    activity = {
                        'id': activity_id_str,
                        'dept': dept,
                        'sem': sem,
                        'course': course,
                        'type': 'theory',
                        'duration': 2,
                        'batch': session,
                        'required': True
                    }
                    activities.append(activity)
                    course_group_map[key].append(activity_id_str)
                    activity_id += 1
                
                # Create lab sessions
                for session in range(lab_hours):
                    activity_id_str = f"A{activity_id}"
                    activity = {
                        'id': activity_id_str,
                        'dept': dept,
                        'sem': sem,
                        'course': course,
                        'type': 'lab',
                        'lab_rooms': course_lab_map.get(course, []),
                        'duration': 2,  # 2-hour lab sessions
                        'batch': session,
                        'required': True
                    }
                    activities.append(activity)
                    course_group_map[key].append(activity_id_str)
                    activity_id += 1

    create_time = time.perf_counter() - start_time
    logger.info(f" Created {len(activities)} activities in {create_time:.2f}s")
    logger.info(f"  - Allocation tracking for {len(allocation_status)} courses")
    return activities, allocation_status, course_group_map


# (Previous imports remain the same)

def create_activities(dept_sem_data, course_lab_map , rooms):
    """Generate scheduling activities with detailed logging"""
    logger.info("\n📝 Creating scheduling activities...")
    start_time = time.perf_counter()
    activities = []
    allocation_status = {}
    course_group_map = defaultdict(list)
    activity_id = 0

    # Diagnostic counters
    total_theory = 0
    total_lab = 0
    courses_with_no_lab_rooms = 0
    courses_with_odd_hours = 0

    for dept, sem_data in dept_sem_data.items():
        for sem, courses in sem_data.items():
            for course, staff_list in courses.items():
                # Get requirements
                theory_hours = staff_list[0]['lecture_hours']
                lab_hours = staff_list[0]['practical_hours']
                
                # Check for odd hours
                if theory_hours % 2 != 0:
                    courses_with_odd_hours += 1
                    logger.warning(f"⚠️ Odd theory hours ({theory_hours}) for {dept}-{sem}-{course}")
                
                # Initialize tracking
                key = (dept, sem, course)
                allocation_status.setdefault(key, {
                    'theory': {'allocated': 0, 'required': (theory_hours + 1) // 2},
                    'lab': {'allocated': 0, 'required': lab_hours}
                })
                
                # Log lab room mapping
                lab_rooms = course_lab_map.get(course, [])
                if lab_hours > 0 and not lab_rooms:
                    courses_with_no_lab_rooms += 1
                    logger.warning(f"⚠️ No lab rooms mapped for {course} (has {lab_hours} lab hours)")
                
                # Create theory sessions
                theory_sessions = (theory_hours + 1) // 2
                for session in range(theory_sessions):
                    activity_id_str = f"A{activity_id}"
                    activity = {
                        'id': activity_id_str,
                        'dept': dept,
                        'sem': sem,
                        'course': course,
                        'type': 'theory',
                        'duration': 2,
                        'batch': session,
                        'required': True,
                        'eligible_rooms': [r for r, (rtype, _) in rooms.items() if rtype == 'classroom']
                    }
                    activities.append(activity)
                    course_group_map[key].append(activity_id_str)
                    activity_id += 1
                    total_theory += 1
                
                # Create lab sessions
                for session in range(lab_hours):
                    activity_id_str = f"A{activity_id}"
                    activity = {
                        'id': activity_id_str,
                        'dept': dept,
                        'sem': sem,
                        'course': course,
                        'type': 'lab',
                        'lab_rooms': lab_rooms,
                        'duration': 2,
                        'batch': session,
                        'required': True,
                        'eligible_rooms': lab_rooms if lab_rooms else [r for r, (rtype, _) in rooms.items() if rtype == 'computer_lab']
                    }
                    activities.append(activity)
                    course_group_map[key].append(activity_id_str)
                    activity_id += 1
                    total_lab += 1

                # Log created activities for this course
                logger.debug(f"   Created {theory_sessions} theory sessions")
                logger.debug(f"   Created {lab_hours} lab sessions")
                if lab_rooms:
                    logger.debug(f"   Lab rooms: {', '.join(lab_rooms)}")

    create_time = time.perf_counter() - start_time
    logger.info(f"✅ Created {len(activities)} activities in {create_time:.2f}s")
    logger.info(f"  - Theory activities: {total_theory}")
    logger.info(f"  - Lab activities: {total_lab}")
    logger.info(f"  - Courses with no lab rooms mapped: {courses_with_no_lab_rooms}")
    logger.info(f"  - Courses with odd theory hours: {courses_with_odd_hours}")
    logger.info(f"  - Allocation tracking for {len(allocation_status)} courses")
    
    # Log sample activities
    if activities:
        logger.debug("\nSample activities created:")
        for i in range(min(3, len(activities))):
            logger.debug(f"  {json.dumps(activities[i], indent=2)}")
    
    return activities, allocation_status, course_group_map

def create_model(activities, allocation_status, course_group_map, rooms):
    """Create model with detailed room eligibility logging"""
    logger.info("\n🧩 Creating optimization model...")
    start_time = time.perf_counter()
    model = cp_model.CpModel()
    
    # Create mappings
    room_map = {name: idx for idx, name in enumerate(rooms.keys())}
    reverse_room_map = {idx: name for name, idx in room_map.items()}
    
    # Log room information
    logger.debug("\n🏢 Room Information:")
    for room_name, (rtype, cap) in rooms.items():
        logger.debug(f"  {room_name}: {rtype} (capacity: {cap})")

    # Create variables with eligibility logging
    logger.info("\n🔧 Creating decision variables with room eligibility...")
    slot_vars = {}
    room_vars = {}
    eligibility_stats = defaultdict(int)
    room_eligibility_issues = 0
    
    for act in activities:
        act_id = act['id']
        slot_vars[act_id] = model.NewIntVar(0, 29, f"slot_{act_id}")
        
        # Use precomputed eligible rooms from activity creation
        eligible_rooms = act['eligible_rooms']
        eligible_room_indices = [room_map[r] for r in eligible_rooms if r in room_map]
        
        # Log eligibility issues
        if not eligible_room_indices:
            room_eligibility_issues += 1
            logger.warning(f"⚠️ No eligible rooms for {act_id} ({act['dept']}-{act['sem']}-{act['course']})")
            logger.warning(f"   Activity type: {act['type']}")
            logger.warning(f"   Attempted rooms: {eligible_rooms}")
            eligible_room_indices = [0]  # Fallback to first room
        
        eligibility_stats[len(eligible_room_indices)] += 1
        room_vars[act_id] = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(eligible_room_indices),
            f"room_{act_id}"
        )
    
    # Log eligibility statistics
    logger.info("\n📊 Room Eligibility Statistics:")
    for count, freq in sorted(eligibility_stats.items()):
        logger.info(f"  {freq} activities have {count} eligible rooms")
    if room_eligibility_issues > 0:
        logger.warning(f"⚠️ {room_eligibility_issues} activities had no eligible rooms and were assigned fallback rooms")

    # (Rest of the constraint creation code remains the same)
    return model, slot_vars, room_vars, room_map, reverse_room_map

class AllocationTracker(cp_model.CpSolverSolutionCallback):
    """Enhanced tracker with detailed unallocation analysis"""
    def __init__(self, activities, allocation_status, rooms, slot_vars, room_vars, room_map, reverse_room_map):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.activities = activities
        self.allocation_status = allocation_status
        self.rooms = rooms
        self.slot_vars = slot_vars
        self.room_vars = room_vars
        self.room_map = room_map
        self.reverse_room_map = reverse_room_map
        self.slot_utilization = {slot: {
            'classrooms_used': 0,
            'classrooms_free': 100,
            'computer_labs_used': 0,
            'computer_labs_free': 42,
            'core_labs_used': 0,
            'core_labs_free': sum(1 for r in rooms.values() if r[0] == 'core_lab')
        } for slot in range(30)}
        self.unallocated_activities = []
        self.solution_count = 0
        self.start_time = time.perf_counter()
        self.schedule = {slot: [] for slot in range(30)}
        self.unallocated_reasons = {}
        self.slot_conflicts = {slot: defaultdict(list) for slot in range(30)}

    def on_solution_callback(self):
        self.solution_count += 1
        current_time = time.perf_counter()
        runtime = current_time - self.start_time
        
        # Reset tracking
        self.unallocated_activities = []
        self.unallocated_reasons = {}
        for key in self.allocation_status:
            for act_type in ['theory', 'lab']:
                self.allocation_status[key][act_type]['allocated'] = 0
        
        for slot in range(30):
            self.slot_utilization[slot] = {
                'classrooms_used': 0,
                'classrooms_free': 100,
                'computer_labs_used': 0,
                'computer_labs_free': 42,
                'core_labs_used': 0,
                'core_labs_free': sum(1 for r in self.rooms.values() if r[0] == 'core_lab')
            }
            self.schedule[slot] = []
            self.slot_conflicts[slot] = defaultdict(list)
        
        # Track allocations
        for act in self.activities:
            act_id = act['id']
            slot = self.Value(self.slot_vars[act_id])
            room_idx = self.Value(self.room_vars[act_id])
            room_name = self.reverse_room_map[room_idx]
            rtype, capacity = self.rooms[room_name]
            
            # Update allocation status
            key = (act['dept'], act['sem'], act['course'])
            self.allocation_status[key][act['type']]['allocated'] += 1
            
            # Update slot utilization
            if rtype == 'classroom':
                self.slot_utilization[slot]['classrooms_used'] += 1
                self.slot_utilization[slot]['classrooms_free'] -= 1
            elif rtype == 'computer_lab':
                self.slot_utilization[slot]['computer_labs_used'] += 1
                self.slot_utilization[slot]['computer_labs_free'] -= 1
            elif rtype == 'core_lab':
                self.slot_utilization[slot]['core_labs_used'] += 1
                self.slot_utilization[slot]['core_labs_free'] -= 1
            
            # Add to schedule
            self.schedule[slot].append({
                'activity': act_id,
                'course': f"{act['dept']}-{act['sem']} {act['course']}",
                'type': act['type'],
                'room': room_name,
                'room_type': rtype
            })
        
        # Find unallocated activities
        for key, status in self.allocation_status.items():
            dept, sem, course = key
            for act_type in ['theory', 'lab']:
                allocated = status[act_type]['allocated']
                required = status[act_type]['required']
                if allocated < required:
                    deficit = required - allocated
                    self.unallocated_activities.append({
                        'dept': dept,
                        'sem': sem,
                        'course': course,
                        'type': act_type,
                        'allocated': allocated,
                        'required': required,
                        'deficit': deficit
                    })
        
        # Analyze unallocated activities
        self.analyze_unallocated()
        
        # Print summary
        logger.info(f"\n🔍 Solution #{self.solution_count} at {runtime:.2f}s")
        logger.info("📊 Allocation Status:")
        self.print_allocation_summary()
        logger.info("\n📈 Slot Utilization:")
        self.print_slot_utilization()
        logger.info("\n❗ Unallocated Activities Analysis:")
        self.print_unallocated_analysis()
        
        # Visualize utilization
        self.visualize_utilization()

    def analyze_unallocated(self):
        """Determine why activities couldn't be allocated"""
        # Track room usage per slot per type
        slot_room_usage = {slot: defaultdict(int) for slot in range(30)}
        slot_room_capacity = {slot: defaultdict(int) for slot in range(30)}
        
        for slot in range(30):
            for act in self.schedule[slot]:
                room_type = act['room_type']
                slot_room_usage[slot][room_type] += 1
        
        # Calculate room capacities
        for room_name, (rtype, cap) in self.rooms.items():
            for slot in range(30):
                slot_room_capacity[slot][rtype] += cap
        
        # Analyze each unallocated activity
        for act in self.unallocated_activities:
            key = (act['dept'], act['sem'], act['course'], act['type'])
            deficit = act['deficit']
            
            # Get sample activity of this type
            sample_act = next((a for a in self.activities 
                             if (a['dept'], a['sem'], a['course']) == (act['dept'], act['sem'], act['course'])
                             and a['type'] == act['type']), None)
            
            if not sample_act:
                self.unallocated_reasons[key] = ["No matching activity found"]
                continue
                
            # Get eligible rooms
            eligible_rooms = sample_act['eligible_rooms']
            eligible_room_types = set(self.rooms[r][0] for r in eligible_rooms if r in self.rooms)
            
            reasons = []
            
            # Check room eligibility
            if not eligible_rooms:
                reasons.append("No eligible rooms specified")
            else:
                # Check each slot for availability
                for slot in range(30):
                    for room_type in eligible_room_types:
                        available = slot_room_capacity[slot][room_type] - slot_room_usage[slot][room_type]
                        if available > 0:
                            break
                    else:
                        reasons.append(f"No {', '.join(eligible_room_types)} rooms available in slot {slot}")
            
            self.unallocated_reasons[key] = {
                'reasons': reasons if reasons else ["Unknown reason"],
                'eligible_rooms': eligible_rooms,
                'eligible_room_types': list(eligible_room_types),
                'deficit': deficit
            }

    def print_unallocated_analysis(self):
        """Detailed analysis of why activities couldn't be allocated"""
        if not self.unallocated_reasons:
            logger.info("✅ All activities allocated successfully!")
            return
        
        headers = ["Dept", "Sem", "Course", "Type", "Deficit", "Reasons", "Eligible Room Types", "Eligible Rooms"]
        rows = []
        
        for (dept, sem, course, act_type), data in sorted(self.unallocated_reasons.items()):
            rows.append([
                dept, sem, course, act_type,
                data['deficit'],
                "\n".join(data['reasons']),
                ", ".join(data['eligible_room_types']),
                ", ".join(data['eligible_rooms']) if data['eligible_rooms'] else "None"
            ])
        
        logger.info("\n" + tabulate(rows, headers=headers, tablefmt="grid"))
        
        # Additional conflict analysis
        logger.info("\n🔍 Most Constrained Resources:")
        constrained_resources = defaultdict(int)
        for _, data in self.unallocated_reasons.items():
            for reason in data['reasons']:
                if "available" in reason:
                    resource = reason.split("rooms")[0].strip()
                    constrained_resources[resource] += data['deficit']
        
        if constrained_resources:
            logger.info("\n".join(f"  {k}: {v} unallocated activities" 
                                for k, v in sorted(constrained_resources.items(), 
                                                 key=lambda x: -x[1])))

# (Rest of the code remains the same)

def initialize_rooms():
    """Create room structure with capacities with timing"""
    logger.info("\n Initializing room resources...")
    start_time = time.perf_counter()
    rooms = {}
    # Computer labs (42 total: 5 special, 37 regular)
    computer_labs = [f"CLab{i}" for i in range(1, 43)]
    for i, room_name in enumerate(computer_labs):
        rooms[room_name] = ('computer_lab', 2 if i < 5 else 1)  # First 5 are special
    
    # Classrooms (100)
    classrooms = [f"Class{i}" for i in range(1, 101)]
    for room_name in classrooms:
        rooms[room_name] = ('classroom', 1)
    
    # Core labs (example)
    core_labs = {
        "Aero CAD Lab": ('core_lab', 1),
        "Aircraft Structures Lab": ('core_lab', 1),
        "Airframe Repair and Aero Engine Lab": ('core_lab', 1),
        "Auto CAD Lab": ('core_lab', 1),
        "Automation Lab": ('core_lab', 1),
        "Automotive Componenets lab": ('core_lab', 1),
        "Avionics Lab": ('core_lab', 1),
        "Baking Lab": ('core_lab', 1),
        "Basic electronics lab-1": ('core_lab', 4),
        "Biochemistry lab": ('core_lab', 1),
        "Bioprocess lab": ('core_lab', 1),
        "Chemical Reaction Engineering Lab": ('core_lab', 1),
        "Chemistry Lab": ('core_lab', 2),
        "Classroom": ('core_lab', 4),
        "Communication Systems Lab": ('core_lab', 1),
        "Concrete & Survey Lab": ('core_lab', 1),
        "DSP Lab": ('core_lab', 1),
        "Diagnostic and Therapeutic Equipment Lab": ('core_lab', 1),
        "Digital Lab": ('core_lab', 2),
        "Downstream Processing Lab": ('core_lab', 1),
        "Dynamics Lab": ('core_lab', 2),
        "Electrical Machines I Lab": ('core_lab', 4),
        "Electronic Devices & Circuits Lab": ('core_lab', 1),
        "Electronics and Instrumentation": ('core_lab', 1),
        "Embedded System Laboratory (ECE)": ('core_lab', 1),
        "Embedded System Laboratory(EEE)": ('core_lab', 1),
        "Engineering Practices Lab (Electrical)": ('core_lab', 2),
        "Engineering Practices Lab (Electronics)": ('core_lab', 2),
        "Fluid Mechanics Lab": ('core_lab', 1),
        "Food Microbiology Lab": ('core_lab', 1),
        "Food Processing and Preservation Lab": ('core_lab', 1),
        "Genetic Engineering Lab": ('core_lab', 1),
        "Immunology Lab": ('core_lab', 1),
        "Industrial Automation Lab": ('core_lab', 1),
        "Isaac Asimov Laboratory": ('core_lab', 2),
        "Livestock Lab": ('core_lab', 1),
        "MCT CAD Lab": ('core_lab', 1),
        "Machine Shop FF1 - EPL": ('core_lab', 4),
        "Manufacturing Technology I": ('core_lab', 1),
        "Mech CAD Lab": ('core_lab', 1),
        "Mechatronics Lab": ('core_lab', 1),
        "Medical Image Processing Lab": ('core_lab', 1),
        "Metrology & Measurement Lab": ('core_lab', 1),
        "Microprocessor Lab": ('core_lab', 2),
        "Microprocessor and Microcontrollers Lab": ('core_lab', 1),
        "Optical and Microwave Lab": ('core_lab', 1),
        "Physics Lab": ('core_lab', 4),
        "Power Electronics Lab": ('core_lab', 1),
        "Power System Simulation Lab": ('core_lab', 1),
        "Process Control Lab": ('core_lab', 1),
        "Strength of Materials Lab": ('core_lab', 1),
        "Thermal Lab": ('core_lab', 2),
        "Vehicle Maintenance Lab": ('core_lab', 1),
        "microbiology lab": ('core_lab', 1),
    }
    
    rooms.update(core_labs)
    
    # Room type counts
    room_counts = defaultdict(int)
    for _, (rtype, _) in rooms.items():
        room_counts[rtype] += 1
    
    init_time = time.perf_counter() - start_time
    logger.info(f" Initialized {len(rooms)} rooms in {init_time:.2f}s")
    for rtype, count in room_counts.items():
        logger.info(f"  - {rtype}: {count}")
    
    return rooms

# ----------------------------
# CONSTRAINT PROGRAMMING MODEL (OPTIMIZED)
# ----------------------------
def create_model(activities, allocation_status, course_group_map, rooms):
    """Create optimized CP-SAT model with detailed logging"""
    logger.info("\n Creating optimization model...")
    start_time = time.perf_counter()
    model = cp_model.CpModel()
    
    # Create mappings
    room_map = {name: idx for idx, name in enumerate(rooms.keys())}
    reverse_room_map = {idx: name for name, idx in room_map.items()}
    room_types = {name: rtype for name, (rtype, _) in rooms.items()}
    
    # Create variables
    logger.info("\n Creating decision variables...")
    var_start = time.perf_counter()
    slot_vars = {}      # {activity_id: slot_var (0-29)}
    room_vars = {}      # {activity_id: room_var}
    
    for act in activities:
        act_id = act['id']
        
        # Time slot (0-29 = 30 slots/week)
        slot_vars[act_id] = model.NewIntVar(0, 29, f"slot_{act_id}")
        
        # Room assignment - Only assign to existing rooms
        if act['type'] == 'theory':
            # Theory: any classroom
            eligible_rooms = [r for r, (rtype, cap) in rooms.items() if rtype == 'classroom']
        else:
            # Lab: only assigned lab rooms
            eligible_rooms = act.get('lab_rooms', [])
            if not eligible_rooms:
                # Fallback to any computer lab if none specified
                eligible_rooms = [r for r, (rtype, cap) in rooms.items() if rtype == 'computer_lab']
        
        # Ensure only existing rooms are used
        eligible_room_indices = [room_map[r] for r in eligible_rooms if r in room_map]
        print("Eligible room indices - " , eligible_room_indices)
        
        if not eligible_room_indices:
            logger.warning(f" No eligible rooms for activity {act_id}")
            # Fallback to first room
            eligible_room_indices = [0]
        
        room_vars[act_id] = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(eligible_room_indices),
            f"room_{act_id}"
        )
    
    var_time = time.perf_counter() - var_start
    logger.info(f" Created variables in {var_time:.2f}s")
    
    # ----------------------------
    # OPTIMIZED HARD CONSTRAINTS
    # ----------------------------
    logger.info("\n Adding hard constraints...")
    
    # 1. Course Group Constraint (Optimized)
    logger.info("   Constraint: All batches for same course must be in same slot")
    group_start = time.perf_counter()
    for key, act_ids in course_group_map.items():
        if len(act_ids) > 1:
            # Use a representative slot variable
            rep_slot = slot_vars[act_ids[0]]
            for act_id in act_ids[1:]:
                model.Add(slot_vars[act_id] == rep_slot)
    group_time = time.perf_counter() - group_start
    logger.info(f"     Course groups constrained in {group_time:.2f}s")
    
    # 2. Student Group Constraint (Optimized)
    logger.info("   Constraint: No overlapping subjects for same dept/sem")
    student_start = time.perf_counter()
    dept_sem_activities = defaultdict(list)
    for act in activities:
        key = (act['dept'], act['sem'])
        dept_sem_activities[key].append(act['id'])
    
    # Pre-calculate slot boolvars
    slot_boolvars = {}
    for slot in range(30):
        for act_id in [a['id'] for a in activities]:
            slot_boolvars[(act_id, slot)] = model.NewBoolVar(f"in_slot_{slot}_{act_id}")
            model.Add(slot_vars[act_id] == slot).OnlyEnforceIf(slot_boolvars[(act_id, slot)])
            model.Add(slot_vars[act_id] != slot).OnlyEnforceIf(slot_boolvars[(act_id, slot)].Not())
    
    # Add constraints
    for key, act_ids in dept_sem_activities.items():
        for slot in range(30):
            slot_activities = [slot_boolvars[(act_id, slot)] for act_id in act_ids]
            model.AddAtMostOne(slot_activities)
    
    student_time = time.perf_counter() - student_start
    logger.info(f"     Student groups constrained in {student_time:.2f}s")
    
    # 3. Room Capacity Constraints (Optimized)
    logger.info("   Constraint: Room capacity limits (OPTIMIZED)")
    room_start = time.perf_counter()
    
    # Create room-slot usage variables
    room_slot_usage = {}
    for room_name, (rtype, capacity) in rooms.items():
        room_idx = room_map[room_name]
        for slot in range(30):
            room_slot_usage[(room_idx, slot)] = model.NewIntVar(0, capacity, f"usage_{room_name}_{slot}")
    
    # Create room-bool variables once
    logger.info("     Creating room assignment indicators...")
    room_boolvars = {}
    for act in activities:
        act_id = act['id']
        for room_name in rooms:
            room_idx = room_map[room_name]
            room_boolvars[(act_id, room_idx)] = model.NewBoolVar(f"in_{room_name}_{act_id}")
            model.Add(room_vars[act_id] == room_idx).OnlyEnforceIf(room_boolvars[(act_id, room_idx)])
            model.Add(room_vars[act_id] != room_idx).OnlyEnforceIf(room_boolvars[(act_id, room_idx)].Not())
    
    # Create combined room-slot indicators
    logger.info("     Creating room-slot indicators...")
    room_slot_indicators = {}
    for (room_idx, slot) in room_slot_usage.keys():
        activities_in_room_slot = []
        for act in activities:
            act_id = act['id']
            both = model.NewBoolVar(f"both_{room_idx}_{slot}_{act_id}")
            model.AddBoolAnd([
                room_boolvars[(act_id, room_idx)],
                slot_boolvars[(act_id, slot)]
            ]).OnlyEnforceIf(both)
            model.AddBoolOr([
                room_boolvars[(act_id, room_idx)].Not(),
                slot_boolvars[(act_id, slot)].Not()
            ]).OnlyEnforceIf(both.Not())
            activities_in_room_slot.append(both)
        
        # Set the usage variable
        model.Add(room_slot_usage[(room_idx, slot)] == sum(activities_in_room_slot))
        # Capacity constraint
        model.Add(room_slot_usage[(room_idx, slot)] <= capacity)
    
    room_time = time.perf_counter() - room_start
    logger.info(f"     Room capacity constrained in {room_time:.2f}s")
    
    model_time = time.perf_counter() - start_time
    logger.info(f" Model created in {model_time:.2f}s")
    return model, slot_vars, room_vars, room_map, reverse_room_map

# ----------------------------
# SOLUTION TRACKING & VISUALIZATION
# ----------------------------
class AllocationTracker(cp_model.CpSolverSolutionCallback):
    """Track allocation status during solving with enhanced visualization"""
    def __init__(self, activities, allocation_status, rooms, slot_vars, room_vars, room_map, reverse_room_map):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.activities = activities
        self.allocation_status = allocation_status
        self.rooms = rooms
        self.slot_vars = slot_vars
        self.room_vars = room_vars
        self.room_map = room_map
        self.reverse_room_map = reverse_room_map
        self.slot_utilization = {slot: {
            'classrooms_used': 0,
            'classrooms_free': 100,
            'computer_labs_used': 0,
            'computer_labs_free': 42,
            'core_labs_used': 0,
            'core_labs_free': sum(1 for r in rooms.values() if r[0] == 'core_lab')
        } for slot in range(30)}
        self.unallocated_activities = []
        self.solution_count = 0
        self.start_time = time.perf_counter()
        self.schedule = {slot: [] for slot in range(30)}

    def on_solution_callback(self):
        self.solution_count += 1
        current_time = time.perf_counter()
        runtime = current_time - self.start_time
        
        # Reset tracking
        self.unallocated_activities = []
        for key in self.allocation_status:
            for act_type in ['theory', 'lab']:
                self.allocation_status[key][act_type]['allocated'] = 0
        
        for slot in range(30):
            self.slot_utilization[slot] = {
                'classrooms_used': 0,
                'classrooms_free': 100,
                'computer_labs_used': 0,
                'computer_labs_free': 42,
                'core_labs_used': 0,
                'core_labs_free': sum(1 for r in self.rooms.values() if r[0] == 'core_lab')
            }
            self.schedule[slot] = []
        
        # Track allocations
        for act in self.activities:
            act_id = act['id']
            slot = self.Value(self.slot_vars[act_id])
            room_idx = self.Value(self.room_vars[act_id])
            room_name = self.reverse_room_map[room_idx]
            rtype, capacity = self.rooms[room_name]
            
            # Update allocation status
            key = (act['dept'], act['sem'], act['course'])
            self.allocation_status[key][act['type']]['allocated'] += 1
            
            # Update slot utilization
            if rtype == 'classroom':
                self.slot_utilization[slot]['classrooms_used'] += 1
                self.slot_utilization[slot]['classrooms_free'] -= 1
            elif rtype == 'computer_lab':
                self.slot_utilization[slot]['computer_labs_used'] += 1
                self.slot_utilization[slot]['computer_labs_free'] -= 1
            elif rtype == 'core_lab':
                self.slot_utilization[slot]['core_labs_used'] += 1
                self.slot_utilization[slot]['core_labs_free'] -= 1
            
            # Add to schedule
            self.schedule[slot].append({
                'activity': act_id,
                'course': f"{act['dept']}-{act['sem']} {act['course']}",
                'type': act['type'],
                'room': room_name,
                'room_type': rtype
            })
        
        # Find unallocated activities
        for key, status in self.allocation_status.items():
            for act_type in ['theory', 'lab']:
                allocated = status[act_type]['allocated']
                required = status[act_type]['required']
                if allocated < required:
                    self.unallocated_activities.append({
                        'dept': key[0],
                        'sem': key[1],
                        'course': key[2],
                        'type': act_type,
                        'allocated': allocated,
                        'required': required,
                        'deficit': required - allocated
                    })
        
        # Print summary
        logger.info(f"\n Solution #{self.solution_count} at {runtime:.2f}s")
        logger.info("Allocation Status:")
        self.print_allocation_summary()
        logger.info("\n Slot Utilization:")
        self.print_slot_utilization()
        logger.info("\n Unallocated Activities:")
        self.print_unallocated()
        
        # Visualize utilization
        self.visualize_utilization()

    def print_allocation_summary(self):
        """Print summary of allocated vs required periods"""
        headers = ["Dept", "Sem", "Course", "Type", "Allocated", "Required", "Status"]
        rows = []
        
        for key, status in self.allocation_status.items():
            dept, sem, course = key
            for act_type in ['theory', 'lab']:
                alloc = status[act_type]['allocated']
                req = status[act_type]['required']
                status_icon = "✅" if alloc >= req else "⚠️" if alloc > 0 else "❌"
                rows.append([
                    dept, sem, course, act_type, 
                    f"{alloc}/{req}", 
                    status_icon
                ])
        
        # Print with tabulate
        logger.info("\n" + tabulate(rows, headers=headers, tablefmt="grid"))

    def print_slot_utilization(self):
        """Print room utilization per slot"""
        headers = ["Slot", "Classrooms", "Computer Labs", "Core Labs"]
        rows = []
        
        for slot in range(30):
            util = self.slot_utilization[slot]
            classrooms = f"{util['classrooms_used']} used, {util['classrooms_free']} free"
            comp_labs = f"{util['computer_labs_used']} used, {util['computer_labs_free']} free"
            core_labs = f"{util['core_labs_used']} used, {util['core_labs_free']} free"
            rows.append([slot, classrooms, comp_labs, core_labs])
        
        # Print with tabulate
        logger.info("\n" + tabulate(rows, headers=headers, tablefmt="grid"))

    def print_unallocated(self):
        """Print unallocated activities"""
        if not self.unallocated_activities:
            logger.info("✅ All activities allocated successfully!")
            return
        
        headers = ["Dept", "Sem", "Course", "Type", "Allocated", "Required", "Deficit"]
        rows = []
        for act in self.unallocated_activities:
            rows.append([
                act['dept'], act['sem'], act['course'], act['type'],
                f"{act['allocated']}/{act['required']}",
                act['deficit']
            ])
        
        # Print with tabulate
        logger.info("\n" + tabulate(rows, headers=headers, tablefmt="grid"))
    
    def visualize_utilization(self):
        """Create visualizations using matplotlib"""
        try:
            # Prepare data for plotting
            slots = list(range(30))
            classroom_used = [self.slot_utilization[s]['classrooms_used'] for s in slots]
            comp_lab_used = [self.slot_utilization[s]['computer_labs_used'] for s in slots]
            core_lab_used = [self.slot_utilization[s]['core_labs_used'] for s in slots]
            
            # Create figure
            plt.figure(figsize=(15, 10))
            
            # Classroom utilization
            plt.subplot(3, 1, 1)
            plt.bar(slots, classroom_used, color='skyblue')
            plt.title('Classroom Utilization')
            plt.xlabel('Time Slot')
            plt.ylabel('Classrooms Used')
            plt.grid(True, linestyle='--', alpha=0.7)
            
            # Computer lab utilization
            plt.subplot(3, 1, 2)
            plt.bar(slots, comp_lab_used, color='lightgreen')
            plt.title('Computer Lab Utilization')
            plt.xlabel('Time Slot')
            plt.ylabel('Computer Labs Used')
            plt.grid(True, linestyle='--', alpha=0.7)
            
            # Core lab utilization
            plt.subplot(3, 1, 3)
            plt.bar(slots, core_lab_used, color='salmon')
            plt.title('Core Lab Utilization')
            plt.xlabel('Time Slot')
            plt.ylabel('Core Labs Used')
            plt.grid(True, linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig(f'utilization_solution_{self.solution_count}.png')
            plt.close()
            logger.info(f" Saved utilization visualization to utilization_solution_{self.solution_count}.png")
            
        except Exception as e:
            logger.error(f" Visualization error: {e}")

# ----------------------------
# MAIN FUNCTION
# ----------------------------
def main():
    logger.info("="*50)
    logger.info(" COLLEGE TIMETABLE GENERATION SYSTEM")
    logger.info("="*50)
    
    # Load and prepare data
    dept_sem_data, course_lab_map = load_data()
    rooms = initialize_rooms()
    activities, allocation_status, course_group_map = create_activities(dept_sem_data, course_lab_map , rooms)
    
    # Create optimization model
    model, slot_vars, room_vars, room_map, reverse_room_map = create_model(
        activities, allocation_status, course_group_map, rooms
    )
    
    # Setup solution tracker
    tracker = AllocationTracker(
        activities, allocation_status, rooms, slot_vars, room_vars, room_map, reverse_room_map
    )
    
    # Solve the model
    logger.info("\n Starting solver...")
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 1200  # 20 minutes
    solver.parameters.num_search_workers = 8  # Use multiple cores
    
    solve_start = time.perf_counter()
    status = solver.Solve(model, tracker)
    solve_time = time.perf_counter() - solve_start
    
    # Print final results
    logger.info("\n" + "="*50)
    logger.info(" FINAL ALLOCATION REPORT")
    logger.info("="*50)
    
    if status == cp_model.OPTIMAL:
        logger.info(" Optimal solution found")
    elif status == cp_model.FEASIBLE:
        logger.info(" Feasible solution found")
    else:
        logger.info(" No solution found")
    
    logger.info(f" Total solve time: {solve_time:.2f} seconds")
    
    # Final allocation status
    logger.info("\n FINAL ALLOCATION STATUS:")
    tracker.print_allocation_summary()
    
    logger.info("\n FINAL SLOT UTILIZATION:")
    tracker.print_slot_utilization()
    
    logger.info("\n FINAL UNALLOCATED ACTIVITIES:")
    tracker.print_unallocated()
    
    # Generate final visualizations
    tracker.visualize_utilization()

if __name__ == '__main__':
    main()