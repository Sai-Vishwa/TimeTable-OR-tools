from ortools.sat.python import cp_model
import math

def schedule_labs(batches, max_lab_hours=60, max_group_size=42):
    """Optimized lab scheduler with batching and staff constraints
    
    Args:
        batches: List of batch dictionaries
        max_lab_hours: Total lab hours available
        max_group_size: Maximum groups per lab session
        
    Returns:
        Tuple of (assigned batches, unassigned batches, total_assigned_hours)
    """
    # Preprocessing: Filter batches with lab hours and calculate per-group requirements
    valid_batches = []
    for batch in batches:
        if batch['required'] <= 0 or batch['groups'] <= 0:
            continue
            
        # Calculate per-group requirements
        per_group_hrs = math.ceil(batch['required'] / batch['groups'])
        valid_batches.append({
            'dept': batch['dept'],
            'year': batch['year'],
            'groups': batch['groups'],
            'per_group_hrs': per_group_hrs,
            'staff': list(set(batch['staff'])),  # Deduplicate staff
            'batch_id': f"{batch['dept']}-{batch['year']}",
            'original': batch  # Keep reference to original data
        })
    
    # Create model
    model = cp_model.CpModel()
    
    # Decision variables
    assignments = {}  # (batch_id, group_index) -> hours assigned
    group_used = {}   # Whether group is assigned
    batch_used = {}   # Whether batch has any groups assigned
    max_per_group_hrs = model.NewIntVar(0, 10, 'max_per_group_hrs')
    
    # Track batches by dept-year
    dept_year_batches = {}
    
    for batch in valid_batches:
        batch_id = batch['batch_id']
        batch_used[batch_id] = model.NewBoolVar(f'batch_used_{batch_id}')
        dept_year = (batch['dept'], batch['year'])
        dept_year_batches.setdefault(dept_year, []).append(batch_id)
        
        # Create variables for each group in the batch
        group_vars = []
        for i in range(batch['groups']):
            var_name = f'{batch_id}_group_{i}'
            # Hours assigned to this group (0 to per_group_hrs)
            hr_var = model.NewIntVar(0, batch['per_group_hrs'], f'hr_{var_name}')
            # Whether this group is used
            used_var = model.NewBoolVar(f'used_{var_name}')
            
            assignments[(batch_id, i)] = hr_var
            group_used[(batch_id, i)] = used_var
            group_vars.append(used_var)
            
            # Link used_var to hr_var
            model.Add(hr_var > 0).OnlyEnforceIf(used_var)
            model.Add(hr_var == 0).OnlyEnforceIf(used_var.Not())
            
            # Constraint: Staff availability
            model.Add(hr_var <= len(batch['staff']))
        
        # Batch is used if any group is used
        model.AddMaxEquality(batch_used[batch_id], group_vars)
    
    # Constraint 1: Dept-Year exclusivity
    for dept_year, batch_ids in dept_year_batches.items():
        # Only one batch per dept-year can be assigned
        model.AddAtMostOne(batch_used[b] for b in batch_ids)
    
    # Constraint 2: Total lab hours
    total_hours = sum(assignments.values())
    model.Add(total_hours <= max_lab_hours)
    
    # Constraint 3: Max group size per session
    total_groups = sum(group_used.values())
    model.Add(total_groups <= max_group_size)
    
    # Constraint 4: Track max per-group hours
    model.AddMaxEquality(max_per_group_hrs, [
        assignments[key] for key in assignments
    ])
    
    # Objective: Minimize max per-group hours + maximize group utilization
    model.Minimize(
        max_per_group_hrs * 1000 +  # Primary: Minimize max hours
        (max_group_size - total_groups) * 100 +  # Secondary: Maximize group usage
        (max_lab_hours - total_hours)  # Tertiary: Use available hours
    )
    
    # Solve model
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    # Extract results
    assigned = []
    unassigned = []
    total_assigned_hours = 0
    
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        # Process batches
        for batch in valid_batches:
            batch_id = batch['batch_id']
            assigned_hrs = 0
            assigned_groups = 0
            
            for i in range(batch['groups']):
                key = (batch_id, i)
                hours = solver.Value(assignments[key])
                if hours > 0:
                    assigned_hrs += hours
                    assigned_groups += 1
            
            if assigned_groups > 0:
                original = batch['original']
                assigned.append({
                    'dept': batch['dept'],
                    'year': batch['year'],
                    'subject': original['subject'],
                    'course_code': original['course_code'],
                    'assigned_hrs': assigned_hrs,
                    'required_hrs': original['required'],
                    'assigned_groups': assigned_groups,
                    'total_groups': batch['groups'],
                    'per_group_hrs': batch['per_group_hrs']
                })
                total_assigned_hours += assigned_hrs
            else:
                unassigned.append(batch['original'])
    
    return assigned, unassigned, total_assigned_hours

# Example Usage
if __name__ == "__main__":
    # Sample data (using your format)
    input_batches = [
        {
            "dept": "Computer Science & Engineering",
            "year": 2,
            "subject": "Object Oriented Programming Using JAVA",
            "course_code": "CS23333",
            "required": 48,
            "staff": ["CS281", "CS171", "CS314", "CS221", "CS178", "CS298", "CS322", "New Staff-10"],
            "total_students": 560,
            "groups": 16
        },
        {
            "dept": "Information Technology",
            "year": 4,
            "subject": "Software Testing",
            "course_code": "IT19P78",
            "required": 36,
            "staff": ["IT240", "IT205"],
            "total_students": 206,
            "groups": 6
        }
        # Add more batches...
    ]
    
    # Run scheduler
    assigned, unassigned, total_hours = schedule_labs(input_batches)
    
    # Print results
    print("Assigned Batches:")
    for batch in assigned:
        print(f"- {batch['dept']} Year {batch['year']}: {batch['subject']} ({batch['course_code']})")
        print(f"  Groups: {batch['assigned_groups']}/{batch['total_groups']} "
              f"| Hours: {batch['assigned_hrs']}/{batch['required_hrs']} "
              f"| Per Group: {batch['per_group_hrs']}h")
    
    print("\nUnassigned Batches (Handle Manually):")
    for batch in unassigned:
        print(f"- {batch['dept']} Year {batch['year']}: {batch['subject']} "
              f"| Required: {batch['required']}h")
    
    print(f"\nTotal Assigned Hours: {total_hours}/60")
    print(f"Remaining Hours: {60 - total_hours}")