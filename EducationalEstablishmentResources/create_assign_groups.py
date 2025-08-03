import math
from django.shortcuts import redirect
from EducationalEstablishmentResources.models import Group, Speciality
from users.models import BasicUserProfile, GroupPreference


def groupCreation(specialities):
    try:
        # Delete existing groups
        Group.objects.filter(speciality__in=specialities).delete()

        for speciality in specialities:
            students = BasicUserProfile.objects.filter(speciality=speciality)
            total = students.count()
            print(f"Speciality: {speciality}, Students: {total}")

            groups_capacity = speciality.level.departement.groupsCapacity
            groups_capacity = groups_capacity if groups_capacity not in [None,0,''] else 30

            groups = max(1, math.ceil(total / groups_capacity))
            print(f"Creating {groups} groups for {speciality} with capacity {groups_capacity}")

            fakeTotal = total  # Keep track of students left to assign
            max_etudiant_per_groupe = math.ceil(total / groups)
            for i in range(1, groups + 1):
                if fakeTotal >= max_etudiant_per_groupe:
                    capacity = max_etudiant_per_groupe
                else:
                    capacity = fakeTotal

                Group.objects.create(speciality=speciality, group_number=i, capacity=capacity)

                fakeTotal -= capacity
                if fakeTotal <= 0:
                    break  # Done assigning all students

        return redirect('/admin/EducationalEstablishmentResources/group/')
    except Exception as e:
        print(f"Error during group creation: {e}")
        return redirect('/admin/EducationalEstablishmentResources/group/')


def assignToGroups(specialities):
    try:
        basicUsers = BasicUserProfile.objects.filter(speciality__in=specialities).order_by('first_name')
        groups = Group.objects.filter(speciality__in=specialities)
        #sort preferences by updated_at date field
        preferences = GroupPreference.objects.filter(user__in=basicUsers).order_by('updated_at')

        #organize preferences by basicUser id
        preference_dict = {pref.user.id: pref.chosenGroup for pref in preferences}

        #organize groups by speciality
        speciality_groups = {}
        for group in groups:
            spc_name = group.speciality.name
            if spc_name not in speciality_groups:
                speciality_groups[spc_name] = []
            speciality_groups[spc_name].append(group)

        #initialize group capacity counters
        group_capacity = {}
        group_current_size = {}
        for group in groups:
            group_capacity[group.id] = group.capacity if group.capacity not in [0, None] else 30
            group_current_size[group.id] = 0  #capture number of students in the group while assigning them to



        #prioritize basic users who made preference first
        basicUsers_sorted = list(basicUsers)
        basicUsers_sorted.sort(key=lambda user: (
            0 if user.id in preference_dict else 1,  #who have chosen a groupe before, come first
            preferences.filter(user=user).first().updated_at if user.id in preference_dict else None))

            #result= either  (0, 2024-07-01)  or (1, None)

        # Assignments
        for basicUser in basicUsers_sorted:
            speciality_name = basicUser.speciality.name
            available_groups = speciality_groups.get(speciality_name, [])

            assigned = False

            # 1-who preferred a group first
            preferred_group = preference_dict.get(basicUser.id)
            if preferred_group and preferred_group in available_groups:
                if group_current_size[preferred_group.id] < group_capacity[preferred_group.id]:
                    basicUser.group = preferred_group
                    basicUser.save()
                    group_current_size[preferred_group.id] += 1
                    assigned = True

            # 2. If no preference or preferred group full, assign to any available group
            if not assigned:
                for group in available_groups:
                    if group_current_size[group.id] < group_capacity[group.id]:
                        basicUser.group = group
                        basicUser.save()
                        group_current_size[group.id] += 1
                        break

        return redirect('/admin/users/basicuserprofile/group/')
    except Exception as e:
        print(f"Error during generation: {e}")
        return redirect('/admin/EducationalEstablishmentResources/group/')
