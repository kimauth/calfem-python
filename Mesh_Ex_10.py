'''Example 10

The use case from the user manual. 
The example does not contain anything that is not covered in the previous examples.
'''

import calfem.core as cfc
import calfem.geometry as cfg
import calfem.mesh as cfm
import calfem.vis as cfv
import calfem.utils as cfu

import numpy as np

from scipy.sparse import lil_matrix

from numba import jit

@jit
def assemElements(K, edof, ex, ey, elementmarkers, elprop, elType):
    
    for eltopo, elx, ely, elMarker in zip(edof, ex, ey, elementmarkers):
    
        if elType == 2:
            Ke = cfc.plante(elx, ely, elprop[elMarker][0], elprop[elMarker][1])
        else:
            Ke = cfc.planqe(elx, ely, elprop[elMarker][0], elprop[elMarker][1])
            
        cfc.assem(eltopo, K, Ke)



# ---- General parameters ---------------------------------------------------

cfu.enableLogging()

t = 0.2
v = 0.35
E1 = 2e9
E2 = 0.2e9
ptype = 1
ep = [ptype,t]
D1 = cfc.hooke(ptype, E1, v)
D2 = cfc.hooke(ptype, E2, v)

# Define marker constants instead of using numbers in the code

markE1 = 55
markE2 = 66
markFixed = 70
markLoad = 90

# Create dictionary for the different element properties

elprop = {}
elprop[markE1] = [ep, D1]
elprop[markE2] = [ep, D2]

# Parameters controlling mesh

elSizeFactor = 0.02    # Element size factor
elType = 3             # Triangle element
dofsPerNode = 2        # Dof per node

# ---- Create Geometry ------------------------------------------------------

# Create a Geometry object that holds the geometry.

g = cfg.Geometry() 

# Add points:

g.point([0, 0])		#0
g.point([1, 0])		#1
g.point([1, 1])		#2
g.point([0, 1])		#3
g.point([0.2, 0.2])	#4
g.point([0.8, 0.2])	#5
g.point([0.8, 0.8])	#6
g.point([0.2, 0.8])	#7

# Add curves:

g.spline([0, 1], marker = markFixed) #0
g.spline([2, 1])                     #1
g.spline([3, 2], marker = markLoad)  #2
g.spline([0, 3])                     #3
g.spline([4, 5])                     #4
g.spline([5, 6])                     #5
g.spline([6, 7])                     #6
g.spline([7, 4])                     #7

# Add surfaces:

g.surface([0,1,2,3], holes = [[4,5,6,7]], marker = markE1)
g.surface([4,5,6,7], marker = markE2)

# ---- Create Mesh ----------------------------------------------------------

meshGen = cfm.GmshMeshGenerator(g)
meshGen.elSizeFactor = elSizeFactor
meshGen.elType = elType  
meshGen.dofsPerNode = dofsPerNode

# Mesh the geometry:
#  The first four return values are the same as those that trimesh2d() returns.
#  value elementmarkers is a list of markers, and is used for finding the 
#  marker of a given element (index).

coords, edof, dofs, bdofs, elementmarkers = meshGen.create()

# ---- Solve problem --------------------------------------------------------

nDofs = np.size(dofs)
K = lil_matrix((nDofs,nDofs))
ex, ey = cfc.coordxtr(edof, coords, dofs)

print("Assembling K... ("+str(nDofs)+")")

assemElements(K, edof, ex, ey, elementmarkers, elprop, elType)

#for eltopo, elx, ely, elMarker in zip(edof, ex, ey, elementmarkers):
#
#    if elType == 2:
#        Ke = cfc.plante(elx, ely, elprop[elMarker][0], elprop[elMarker][1])
#    else:
#        Ke = cfc.planqe(elx, ely, elprop[elMarker][0], elprop[elMarker][1])
#        
#    cfc.assem(eltopo, K, Ke)
    
print("Applying bc and loads...")

bc = np.array([],'i')
bcVal = np.array([],'i')

bc, bcVal = cfu.applybc(bdofs, bc, bcVal, markFixed, 0.0)

f = np.zeros([nDofs,1])

cfu.applyforcetotal(bdofs, f, markLoad, value = -10e5, dimension=2)

print("Solving system...")

a,r = cfc.spsolveq(K, f, bc, bcVal)

print("Extracting ed...")

ed = cfc.extractEldisp(edof, a)
vonMises = []

# ---- Calculate elementr stresses and strains ------------------------------

print("Element forces... ")

for i in range(edof.shape[0]):
    
    # Handle triangle elements
        
    if elType == 2: 
        es, et = cfc.plants(ex[i,:], ey[i,:], 
                        elprop[elementmarkers[i]][0], 
                        elprop[elementmarkers[i]][1], 
                        ed[i,:])
        
        vonMises.append( np.math.sqrt( pow(es[0,0],2) - es[0,0]*es[0,1] + pow(es[0,1],2) + 3*pow(es[0,2],2) ) )

    else:
        
        # Handle quad elements
        
        es, et = cfc.planqs(ex[i,:], ey[i,:], 
                        elprop[elementmarkers[i]][0], 
                        elprop[elementmarkers[i]][1], 
                        ed[i,:])
        
        vonMises.append( np.math.sqrt( pow(es[0],2) - es[0]*es[1] + pow(es[1],2) + 3*pow(es[2],2) ) )
        
# ---- Visualise results ----------------------------------------------------

print("Drawing results...")

cfv.drawGeometry(g, title="Geometry")

cfv.figure() 
cfv.drawMesh(coords=coords, edof=edof, dofsPerNode=dofsPerNode, elType=elType, 
             filled=True, title="Mesh") #Draws the mesh.

cfv.figure()
cfv.drawDisplacements(a, coords, edof, dofsPerNode, elType, 
                      doDrawUndisplacedMesh=False, title="Displacements", 
                      magnfac=25.0)

cfv.figure()
cfv.drawElementValues(vonMises, coords, edof, dofsPerNode, elType, a, 
                      doDrawMesh=True, doDrawUndisplacedMesh=False, 
                      title="Effective Stress", magnfac=25.0)
                      
cfv.colorBar().SetLabel("Effective stress")

print("Done drawing...")

cfv.showAndWait()