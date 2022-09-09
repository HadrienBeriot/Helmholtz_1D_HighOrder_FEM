
def Lobatto(xi, Order):
    import numpy as np
    Lo = np.zeros((np.size(xi), 9))
    Lo[:, 0] = (1-xi)/2
    Lo[:, 1] = (1+xi)/2
    Lo[:, 2] = (1/2)*(3/2)**(1/2)*(-1+xi**2)
    Lo[:, 3] = (1/2)*(5/2)**(1/2)*(xi*((-1)+xi**2))
    Lo[:, 4] = (1/8)*(7/2)**(1/2)*(1+xi**2*((-6)+5*xi**2))
    Lo[:, 5] = (3/8)*2**(-1/2)*(xi*(3+xi**2*((-10)+7*xi**2)))
    Lo[:, 6] = (1/16)*(11/2)**(1/2)*((-1)+xi**2*(15+xi**2*((-35)+21*xi**2)))
    Lo[:, 7] = (1/16)*(13/2)**(1/2) * \
        (xi*((-5)+xi**2*(35+xi**2*((-63)+33*xi**2))))
    Lo[:, 8] = (1/128)*(15/2)**(1/2) * \
        (5+xi**2*((-140)+xi**2*(630+xi**2*((-924)+429*xi**2))))
    return Lo[:, 0:Order+1]


def LobattoDerivative(xi, Order):
    import numpy as np
    dLo = np.zeros((np.size(xi), 9))
    dLo[:, 0] = -1/2+xi*0
    dLo[:, 1] = 1/2+xi*0
    dLo[:, 2] = (1/2)*(3/2)**(1/2)*(2*xi)
    dLo[:, 3] = (1/2)*(5/2)**(1/2)*((-1)+3*xi**2)
    dLo[:, 4] = (1/8)*(7/2)**(1/2)*(xi*((-12)+20*xi**2))
    dLo[:, 5] = (3/8)*2**(-1/2)*(3+xi**2*((-30)+35*xi**2))
    dLo[:, 6] = (1/16)*(11/2)**(1/2)*(xi*(30+xi**2*((-140)+126*xi**2)))
    dLo[:, 7] = (1/16)*(13/2)**(1/2) * \
        ((-5)+xi**2*(105+xi**2*((-315)+231*xi**2)))
    dLo[:, 8] = (1/128)*(15/2)**(1/2) * \
        (xi*((-280)+xi**2*(2520+xi**2*((-5544)+3432*xi**2))))
    return dLo[:, 0:Order+1]


def Mesh1D(DuctLength, NrOfElem):
    import numpy as np
    NrOfNodes = NrOfElem+1
    Coord = np.linspace(0, DuctLength, NrOfNodes)
    Element = np.zeros((2, NrOfElem))
    Element[0, :] = np.arange(0, NrOfElem)
    Element[1, :] = np.arange(1, NrOfElem+1)
    return NrOfNodes, Coord, Element


def CreateDofs(NrOfNodes, NrOfElem, Element, Order):
    import numpy as np
    NrOfDofs = NrOfNodes + NrOfElem*(Order-1)
    DofNode = np.arange(0, NrOfNodes).astype(int)
    DofElement = np.zeros((Order+1, NrOfElem))
    for iElem in np.arange(NrOfElem):
        # node dofs
        DofElement[0:2, iElem] = DofNode[Element[:, iElem].astype(int)]
        # interior dofs
        DofElement[2:Order+1, iElem] = np.arange(NrOfNodes+(iElem)*(
            Order-1), NrOfNodes+(iElem+1)*(Order-1)).astype(int)
    return NrOfDofs, DofNode, DofElement

def MassAndStiffness_1D(iElem, Order, Coord, Element):
  import numpy as np

  Ke = np.zeros((Order+1, Order+1), dtype=np.complex128)
  Me = np.zeros((Order+1, Order+1), dtype=np.complex128)

  x1 = Coord[Element[0, iElem-1].astype(int)]
  x2 = Coord[Element[1, iElem-1].astype(int)]
  Le = (x2-x1)
  # quadrature rule (integration order 2*Order
  GaussPoints, GaussWeights = np.polynomial.legendre.leggauss(int(2*Order))
  NrOfGaussPoints = GaussWeights.size
  # Loop over the Gauss points
  for n in np.arange(0, NrOfGaussPoints):
      xi = GaussPoints[n]
      # High-order Lobatto shape functions
      L = Lobatto(xi, Order)
      dLdxi = LobattoDerivative(xi, Order)
      dLdx = 2/Le*dLdxi
      # Elementary matrices
      Ke += GaussWeights[n]*np.outer(dLdx, dLdx)*Le/2
      Me += GaussWeights[n]*np.outer(L, L)*Le/2
  return Ke, Me


def GetSolutionOnSubgrid(Sol, Order, Coord, Element, NrOfElem, DofElement, NrOfWavesOnDomain):
  # create a finer subgrid to interpolate the numerical solution
  import numpy as np
  # use a sampling of 20 points per wavelength for plotting
  NrOfSubgridPoints = np.ceil(NrOfWavesOnDomain*20).astype(int)
  #
  xi = np.linspace(-1., 1., NrOfSubgridPoints)
  L = Lobatto(xi, Order)
  x_visu = np.zeros((NrOfSubgridPoints, NrOfElem))
  u_visu = np.zeros((NrOfSubgridPoints, NrOfElem), dtype=np.complex128)
  # Construct solution for each element
  for iElem in np.arange(0, NrOfElem):
    ElemDofs = DofElement[:, iElem]
    # dofs of the element
    x_nodes = Coord[Element[0: 2, iElem].astype(int)]
    # geometrical "hat" shape functions
    N1 = (1-xi)/2; N2 = (1+xi)/2
    # mapping from reference to physical domaim
    x_visu[:, iElem] = N1*x_nodes[0] + N2*x_nodes[1]
    # Numerical solution on subgrid 
    ElemSol = Sol[ElemDofs.astype(int)]
    u_visu[:, iElem] = np.dot(L,ElemSol).flatten()

  x_visu = x_visu.flatten('F')
  u_visu = u_visu.flatten('F')
  
  return x_visu, u_visu


def ComputeFullSolution(DuctLength,NrOfElem,Order,omega,rho0,c0,Vn,beta):
  # performs the numerical simulation for these inputs
  import numpy as np
  import math
  
  # first create the mesh and the Dofs list
  NrOfNodes, Coord, Element = Mesh1D(DuctLength,NrOfElem)
  NrOfDofs, DofNode, DofElement = CreateDofs(NrOfNodes,NrOfElem,Element,Order)

  Matrix = np.zeros((NrOfDofs,NrOfDofs), dtype=np.complex128)
  Rhs = np.zeros((NrOfDofs,1), dtype=np.complex128)
  for iElem in np.arange(0,NrOfElem):
      # call the function returning the mass and stifness element matrices
      Ke, Me = MassAndStiffness_1D(iElem, Order, Coord, Element)
      ElemDofs = (DofElement[:,iElem]).astype(int)
      # assemble - [side note "irregular slice" requires np.ix_ in python]
      Matrix[np.ix_(ElemDofs,ElemDofs)] += Ke - (omega/c0)**2*Me

  # now apply impedance boundary condition at last node
  Matrix[DofNode[NrOfNodes-1],DofNode[NrOfNodes-1]] += 1j*omega/c0*beta

  # and the velocity at first node 
  Rhs[DofNode[0]] = 1j*omega*rho0*Vn

  # solve the sparse system of equations 
  Sol = np.linalg.solve(Matrix, Rhs) 
  
  # compute solution on subgrid
  Lambda = 2*math.pi/(omega/c0); NrOfWavesOnDomain = DuctLength/Lambda
  x_sub, u_h_sub = GetSolutionOnSubgrid(Sol, Order, Coord, Element, NrOfElem, DofElement, NrOfWavesOnDomain)
  
  # exact solution on subgrid 
  u_exact_sub = np.exp(-1j*omega/c0*x_sub)

  E2 = np.linalg.norm(u_h_sub - u_exact_sub)/np.linalg.norm(u_exact_sub)*100
  #print('-' *100 +'\n'+' Numerical error is %1.4g' %E2 + ' % \n' +'-' *100)
  
  return E2, NrOfDofs