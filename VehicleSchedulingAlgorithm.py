import numpy as np
import sys

#****************CONFIG VARIABLES***************************
nrOfZones = Visum.Net.Zones.Count
nrOfIntervals = int(Visum.Net.AttValue("AV_NumOfIntervals"))
nrOfDecimals = int(Visum.Net.AttValue("AV_NumOfDecimals"))

maxIntervals = nrOfIntervals						# maximal number of time intervals that are used for relocation
MaNameTime_ZI = '5001 TT0_Scooter_ZI'				# number and name of distance matrix in time intervals

# matrix number for empty trips in first time interval
MaNoLeerZI1_CS = 7001


#******************GET VALUES FROM VISUM**************************
#Create containers for attributes values

demandAttValues = []
intervalAttValues = ['MatValue(' + MaNameTime_ZI + ')']		#set distances
art = Visum.Net.AttValue("AV_Umlaufbildung_Art")

for i in range (1, nrOfIntervals+1):
#matrix number and name for service trips, zfill might need to be adjusted
    if art == "CS":
		demandAttValues.append('MatValue(6' + str(i).zfill(3) + ' Scooter_Last_ZI_' + str(i).zfill(3))


#Retrieve values from Visum
demandArray = Visum.Net.ODPairs.GetMultipleAttributes(demandAttValues)
demandArray = [list(i) for i in demandArray]

intervalArray = Visum.Net.ODPairs.GetMultipleAttributes(intervalAttValues)
intervalArray = [list(i) for i in intervalArray]

#Create numpy arrays
input_matrix =np.array(demandArray)
input_matrix = np.round(input_matrix, nrOfDecimals)
input_matrix = input_matrix.reshape(nrOfZones, nrOfZones, nrOfIntervals)
input_matrix[input_matrix < 0.0 ] = 0.0

intervalValues = np.array(intervalArray)
intervalValues = intervalValues.astype(int)
distInterval = intervalValues.reshape(nrOfZones, nrOfZones)
distInterval[distInterval < 1] = 1
np.fill_diagonal(distInterval,1)

#Create container for solution matrix
solution_matrix = np.zeros(shape=(nrOfZones,nrOfZones,nrOfIntervals))

#****************************************FUNCTIONS*******************************************************#
def getMaximalDistance (d_st):
    maxDistance = np.max(d_st)
    return maxDistance

def find_tours(d_st, x_sti, y_sti, S, I):
    global z_S
    global availableVehicles
    global nrOfDecimals
    global allVehicles

    # /**********ALLOCATE MEMORY FOR CONTAINERS********************
    # Vehicles that start in zone s in the first time zone
    z_S = np.zeros(shape=(S))

    # Vehicles that are available in zone s at the beginning of time interval i
    availableVehicles = np.zeros(shape=(S,I))

    maxDistance = getMaximalDistance(d_st)

    # Fill maps with neighbouring zones for each distance: zoneId -> (distance -> zones) */
    allNeighboursTo = dict()
    for s in range(S):
        neighboursToS = dict()
        for t in range(S):
            if t != s:
                if (d_st[t, s]) not in neighboursToS:			# s,t zu t,s geaendert
                    neighboursToS[(d_st[t, s])] = list()		# s,t zu t,s geaendert
                neighboursToS.get((d_st[t, s])).append(t)		# s,t zu t,s geaendert
        allNeighboursTo.update({s: neighboursToS})

    #Algorithm
    # Go through network

    # Set the flow to accommodate the demand
    y_sti[:,:,:] = x_sti[:,:,:]

    for i in xrange(I):
        # Consider zone by zone
        for s in xrange(S):

            # Compute the total demand at zone s in time interval i
            demand_si = x_sti[s,:,i].sum()

            # Consider each link in network and its demand
            for t in xrange(S):
                # Add the routed vehicles to the available vehicles at their destination (only if still in range)
                if (i + (d_st[s,t])) < I:
                    availableVehicles[t,i + d_st[s,t]] += y_sti[s,t,i]

            #Check where to get the needed vehicles from (same zone, other zones or acquisition)
            consider_vertex(S,s, i, I, x_sti, y_sti, z_S, availableVehicles, maxDistance, maxIntervals, allNeighboursTo, nrOfDecimals, demand_si)

            #If there are still vehicles available, let them stay in the zone
            if (availableVehicles[s,i] > 0.0):
                y_sti[s,s,i] += round(availableVehicles[s,i], nrOfDecimals)
                if ((i + 1) < I):
                    availableVehicles[s,(i + 1)] += availableVehicles[s,i]

    #compute the sum of all needed vehicles
    allVehicles = 0.0
    for s in xrange(S):
        allVehicles += z_S[s]
    return allVehicles

def consider_vertex(S,s, i, I, x_sti,y_sti,z_S, availableVehicles, maxDistance, maxIntervals, allNeighboursTo,nrOfDecimals,demand_si):

    #check whether enough vehicles are available in s at i
    if round(availableVehicles[s,i],nrOfDecimals) >= round(demand_si,nrOfDecimals):
        #// if so, subtract the demand and go on to next vertex
        availableVehicles[s,i] -= demand_si
        availableVehicles[s, i] = round(availableVehicles[s, i], nrOfDecimals)
        if availableVehicles[s, i] == -0.0:
            availableVehicles[s, i] = 0.0
    else:
        #otherwise, compute how many vehicles are needed additionally
        neededVehicles = round(demand_si - availableVehicles[s,i],nrOfDecimals)

        #reduce available vehicles to zero as all are used
        availableVehicles[s,i] = 0.0

        #try to get the needed vehicles from other zones and safe the number in a new local variable
        foundVehicles = try_to_get(neededVehicles, S, I, s, i, maxDistance, maxIntervals, allNeighboursTo, availableVehicles, y_sti, x_sti, nrOfDecimals)

        #acquire additional vehicles if needed and add them to the previous flow
        if (neededVehicles - foundVehicles) > 0.0:
            acquire_new_vehicles(z_S, y_sti, s, i, (neededVehicles - foundVehicles), nrOfDecimals)

def try_to_get(neededVehicles, S, I, s, i, maxDistance, maxIntervals, allNeighboursTo, availableVehicles, y_sti, x_sti, nrOfDecimals):
    global notNeededVehiclesAtNeighbour

    # variable to track how many vehicles were found
    foundVehicles = 0.0

    # check first the neighboring zones that are close
    for dist in xrange(1, min(min(maxDistance, maxIntervals), i)+1):

        if allNeighboursTo.get(s).get(dist) is None:
            allNeighboursTo.get(s).update({dist:set()})

        # Check all neighbours that are exactly dist far away
        for neighbour in allNeighboursTo.get(s).get(dist):
            # What is the maximal number of vehicles available in the (dist) last time intervals?
            availableAtNeighbour = sys.float_info.max
            for time in range(i - dist, i):
                availableAtNeighbour = min(availableAtNeighbour, availableVehicles[neighbour, time])

            # Compute how many vehicles are available in current time slice
            notNeededVehiclesAtNeighbour = 0

            # If neighbour was already treated, check the available vehicles there
            if neighbour < s:
                notNeededVehiclesAtNeighbour = availableVehicles[neighbour, i]

            #If neighbour was not treated yet, leave enough for the outgoing demand there
            else:
                outgoingDemand = outgoing_demand(S, neighbour, i, x_sti)
                notNeededVehiclesAtNeighbour = max(0.0, (availableVehicles[neighbour, i] - outgoingDemand))

            availableAtNeighbour = min(availableAtNeighbour, notNeededVehiclesAtNeighbour)

            #Check whether more vehicles than needed are found and take only as many as needed
            if (foundVehicles + availableAtNeighbour) >= neededVehicles:
                availableAtNeighbour = neededVehicles - foundVehicles

            #Take vehicles that are available at the neighbor and undo routing
            for time in range(i - dist, i):
                availableVehicles[neighbour, time] -= availableAtNeighbour
                y_sti[neighbour, neighbour, time] -= round(availableAtNeighbour, nrOfDecimals)

            availableVehicles[neighbour, i] -= availableAtNeighbour

            # Consider also current time slice: If neighbour was already treated, remove routing also there
            # as well as the available vehicles in the following time slice
            if neighbour < s:
                if ((i + 1) < I):
                     availableVehicles[neighbour, i + 1] -= availableAtNeighbour

                y_sti[neighbour,neighbour,i] -= round(availableAtNeighbour, nrOfDecimals)

            # Route vehicles that are available at the neighbor to current zone
            y_sti[neighbour, s, (i - dist)] += round(availableAtNeighbour, nrOfDecimals)

            # Add them to found vehicles
            foundVehicles += availableAtNeighbour

            # Return early if sufficiently many vehicles are found
            if round(foundVehicles,nrOfDecimals) == round(neededVehicles,nrOfDecimals):
                return foundVehicles

    return foundVehicles

def outgoing_demand(S, s,i,x_sti):
    outgoingDemand = x_sti[s,:,i].sum()
    return outgoingDemand

def acquire_new_vehicles(z_S,y_sti, s, I, additionalVehicles, nrOfDecimals):
    #Add the acquired vehicles to the current zone already in the first time interval let them stay there
    z_S[s] += round(additionalVehicles, nrOfDecimals)
    for i in xrange(I):
        y_sti[s,s,i] += round(additionalVehicles, nrOfDecimals)

def check_solution_for_feasibility(solution):
    global isFeasible, feasibilityWarnings
    nrOfWarnings = 0

    notSatisfiedDemand = set()

    #check whether flow is non negative
    negative_flow = np.argwhere(final_solution < 0)
    if len(negative_flow) > 0:
        isFeasible = False
    for i in negative_flow:
        feasibilityWarnings += "\n" + "Flow negative at arc " + str(i)
        nrOfWarnings += 1

    #check whether demand is satisfied
    demand_not_satisfied = np.argwhere(np.greater(input_matrix, np.round(solution_matrix,nrOfDecimals)) == True)
    if len(demand_not_satisfied) > 0:
        isFeasible = False
    for i in demand_not_satisfied:
        notSatisfiedDemand.add(str(i))


    if len(notSatisfiedDemand) != 0:
        feasibilityWarnings += "\n" + "Demand not satisfied on the following arcs (s,t,i) = "
        for s in notSatisfiedDemand:
            feasibilityWarnings += str(s) + "\n"
            nrOfWarnings += 1
    #check whether flow is consistent
    for s in range(nrOfZones):
        for i in range(1, nrOfIntervals):

            incoming = 0
            outgoing = 0

            # Compute incoming and outgoing flow
            dist_values = distInterval[:, s]
            dist_values_test = -1 * dist_values + i
            dist_values_index_t = np.argwhere(dist_values_test >= 0)
            dist_values_test = dist_values_test[dist_values_index_t]

            incoming += round(solution_matrix[dist_values_index_t.tolist(),s, dist_values_test.tolist()].sum(), nrOfDecimals)
            outgoing += round(solution[s, :, i].sum(), nrOfDecimals)

            if (incoming != outgoing):
                feasibilityWarnings += "\n" + "Flow not consistent in the following event (s,i) = (" + str((s+1)) + "," + str((i+1)) + "): in=" + str(incoming) + "!=" + str(outgoing) + "=out|\n"
                nrOfWarnings += 1
                isFeasible = False

    return isFeasible, feasibilityWarnings

def solveProblem():
    result = find_tours(distInterval, input_matrix, solution_matrix, nrOfZones, nrOfIntervals)
    return result

#*********************************RUNNING THE PROGRAM*******************************
result = solveProblem()
final_solution = solution_matrix - input_matrix
final_solution[abs(final_solution) < 0.000001] = 0.0

isFeasible = True
feasibilityWarnings = ""
check_solution_for_feasibility(solution_matrix)


#*****************************SET SOLUTION VALUES TO VISUM************************
output_solution = final_solution.reshape(nrOfZones*nrOfZones,nrOfIntervals)

if art == "CS":
    for i in range(nrOfIntervals):
        matrix = output_solution[:,i]

        matrix = matrix.reshape(nrOfZones,nrOfZones)
        matrix = matrix.tolist()
        matrix = tuple([tuple(x) for x in matrix])

        matValues = Visum.Net.Matrices.ItemByKey(MaNoLeerZI1_CS + i)
        matValues.SetValues(matrix)

    Visum.Net.SetAttValue("AV_NumVeh_CS", str(allVehicles))	# set attribute AV_NumVeh_CS
    if isFeasible == True:
        Visum.Net.SetAttValue("AV_Umlaufbildung_Status_CS", "Solution passed feasibility check")	# set attribute AV_Umlaufbildung_Status_CS
    else:
        Visum.Net.SetAttValue("AV_Umlaufbildung_Status_CS", feasibilityWarnings)	# set attribute AV_Umlaufbildung_Status_CS