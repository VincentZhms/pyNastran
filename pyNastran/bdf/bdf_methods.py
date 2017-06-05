"""
This file contains additional methods that do not directly relate to the
reading/writing/accessing of BDF data.  Such methods include:
  - mass_poperties
      get the mass & moment of inertia of the model
  - sum_forces_moments
      find the net force/moment on the model
  - sum_forces_moments_elements
      find the net force/moment on the model for a subset of elements
  - resolve_grids
      change all nodes to a specific coordinate system
  - unresolve_grids
      puts all nodes back to original coordinate system
"""
from __future__ import (nested_scopes, generators, division, absolute_import,
                        print_function, unicode_literals)
from collections import defaultdict
from copy import deepcopy
from codecs import open

from six import iteritems, PY2
from six.moves import zip

from numpy import array

from pyNastran.utils import integer_types
from pyNastran.bdf.bdf_interface.attributes import BDFAttributes
from pyNastran.bdf.methods.mass_properties import (
    _mass_properties_elements_init, _mass_properties_no_xref, _apply_mass_symmetry,
    _mass_properties)
from pyNastran.bdf.methods.loads import sum_forces_moments, sum_forces_moments_elements

from pyNastran.bdf.field_writer_8 import print_card_8
from pyNastran.bdf.field_writer_16 import print_card_16


class BDFMethods(BDFAttributes):
    """
    Has the following methods:
        mass_properties(element_ids=None, reference_point=None, sym_axis=None,
            scale=None)
        resolve_grids(cid=0)
        unresolve_grids(model_old)
        sum_forces_moments_elements(p0, loadcase_id, eids, nids,
            include_grav=False, xyz_cid0=None)
        sum_forces_moments(p0, loadcase_id, include_grav=False,
            xyz_cid0=None)
    """

    def __init__(self):
        BDFAttributes.__init__(self)

    def get_area_breakdown(self, property_ids=None, sum_bar_area=True):
        """
        gets a breakdown of the area by property region

        TODO: What about CONRODs?
        #'PBRSECT',
        #'PBCOMP',
        #'PBMSECT',
        #'PBEAM3',
        #'PBEND',
        #'PIHEX',
        #'PCOMPS',
        """
        skip_props = [
            'PSOLID', 'PLPLANE', 'PPLANE', 'PELAS',
            'PDAMP', 'PBUSH', 'PBUSH1D', 'PBUSH2D',
            'PELAST', 'PDAMPT', 'PBUSHT', 'PDAMP5',
            'PFAST', 'PGAP', 'PRAC2D', 'PRAC3D', 'PCONEAX', 'PLSOLID',
            'PCOMPS', 'PVISC', 'PBCOMP', 'PBEND',
        ]
        #skip_elems = []

        pid_eids = self.get_element_ids_dict_with_pids(property_ids)
        pids_to_area = {}
        for pid, eids in iteritems(pid_eids):
            prop = self.properties[pid]
            areas = []
            if prop.type in ['PSHELL', 'PCOMP', 'PSHEAR', 'PCOMPG', ]:
                for eid in eids:
                    elem = self.elements[eid]
                    try:
                        areas.append(elem.Area())
                    except AttributeError:
                        print(prop)
                        print(elem)
                        raise
            elif prop.type in ['PBAR', 'PBARL', 'PBEAM', 'PBEAML', 'PROD', 'PTUBE']:
                for eid in eids:
                    elem = self.elements[eid]
                    try:
                        if sum_bar_area:
                            areas.append(elem.Area())
                        else:
                            areas = [elem.Area()]
                    except AttributeError:
                        print(prop)
                        print(elem)
                        raise
            elif prop.type in skip_props:
                pass
            else:
                raise NotImplementedError(prop)
            if areas:
                pids_to_area[pid] = sum(areas)
        return pids_to_area

    def get_volume_breakdown(self, property_ids=None):
        """
        gets a breakdown of the volume by property region

        TODO: What about CONRODs?
        #'PBRSECT',
        #'PBCOMP',
        #'PBMSECT',
        #'PBEAM3',
        #'PBEND',
        #'PIHEX',
        """
        pid_eids = self.get_element_ids_dict_with_pids(property_ids)

        no_volume = [
            'PLPLANE', 'PPLANE', 'PELAS',
            'PDAMP', 'PBUSH', 'PBUSH1D', 'PBUSH2D',
            'PELAST', 'PDAMPT', 'PBUSHT', 'PDAMP5',
            'PFAST', 'PGAP', 'PRAC2D', 'PRAC3D', 'PCONEAX',
            'PVISC', 'PBCOMP', 'PBEND',
        ]
        pids_to_volume = {}
        skipped_eid_pid = set([])
        for pid, eids in iteritems(pid_eids):
            prop = self.properties[pid]
            volumes = []
            if prop.type in ['PSHELL', 'PSHEAR']:
                t = prop.t
                areas = []
                for eid in eids:
                    elem = self.elements[eid]
                    areas.append(elem.Area())
                volumesi = [area * t for area in areas]
                volumes.extend(volumesi)
            elif prop.type in ['PCOMP', 'PCOMPG',]:
                areas = []
                for eid in eids:
                    elem = self.elements[eid]
                    areas.append(elem.Area())
                t = prop.Thickness()
                volumesi = [area * t for area in areas]
                volumes.extend(volumesi)
            elif prop.type in ['PBAR', 'PBARL', 'PBEAM', 'PBEAML', 'PROD', 'PTUBE']:
                # what should I do here?
                lengths = []
                for eid in eids:
                    elem = self.elements[eid]
                    length = elem.Length()
                    lengths.append(length)
                area = prop.Area()
                volumesi = [area * length for length in lengths]
                volumes.extend(volumesi)
            elif prop.type in ['PSOLID', 'PCOMPS', 'PLSOLID']:
                for eid in eids:
                    elem = self.elements[eid]
                    if elem.type in ['CTETRA', 'CPENTA', 'CHEXA']:
                        volumes.append(elem.Volume())
                    else:
                        key = (elem.type, prop.type)
                        if key not in skipped_eid_pid:
                            skipped_eid_pid.add(key)
                            self.log.debug('skipping volume %s' % str(key))
            elif prop.type in no_volume:
                pass
            else:
                raise NotImplementedError(prop)
            if volumes:
                pids_to_volume[pid] = sum(volumes)
        return pids_to_volume

    def get_mass_breakdown(self, property_ids=None):
        """
        gets a breakdown of the mass by property region

        TODO: What about CONRODs, CONM2s?
        #'PBRSECT',
        #'PBCOMP',
        #'PBMSECT',
        #'PBEAM3',
        #'PBEND',
        #'PIHEX',
        #'PCOMPS',
        """
        pid_eids = self.get_element_ids_dict_with_pids(property_ids)

        mass_type_to_mass = {}
        pids_to_mass = {}
        skipped_eid_pid = set([])
        for eid, elem in iteritems(self.masses):
            if elem.type not in mass_type_to_mass:
                mass_type_to_mass[elem.type] = elem.Mass()
            else:
                mass_type_to_mass[elem.type] += elem.Mass()

        for pid, eids in iteritems(pid_eids):
            prop = self.properties[pid]
            masses = []
            if prop.type in ['PSHELL', 'PSHEAR']:
                t = prop.t
                nsm = prop.nsm
                rho = prop.Rho()
                for eid in eids:
                    elem = self.elements[eid]
                    area = elem.Area()
                    masses.append(area * (rho * t + nsm))
            elif prop.type in ['PCOMP', 'PCOMPG']:
                for eid in eids:
                    elem = self.elements[eid]
                    masses.append(elem.Mass())
            elif prop.type in ['PBAR', 'PBARL', 'PBEAM', 'PBEAML', 'PROD', 'PTUBE']:
                # what should I do here?
                nsm = prop.nsm
                rho = prop.Rho()
                for eid in eids:
                    elem = self.elements[eid]
                    area = prop.Area()
                    length = elem.Length()
                    masses.append(area * (rho * length + nsm))
            elif prop.type in ['PSOLID', 'PCOMPS', 'PLSOLID']:
                rho = prop.Rho()
                for eid in eids:
                    elem = self.elements[eid]
                    if elem.type in ['CTETRA', 'CPENTA', 'CHEXA']:
                        masses.append(rho * elem.Volume())
                    else:
                        key = (elem.type, prop.type)
                        if key not in skipped_eid_pid:
                            skipped_eid_pid.add(key)
                            self.log.debug('skipping mass %s' % str(key))
            elif prop.type in ['PLPLANE', 'PPLANE', 'PELAS',
                               'PDAMP', 'PBUSH', 'PBUSH1D', 'PBUSH2D',
                               'PELAST', 'PDAMPT', 'PBUSHT', 'PDAMP5',
                               'PFAST', 'PGAP', 'PRAC2D', 'PRAC3D', 'PCONEAX',
                               'PVISC', 'PBCOMP', 'PBEND']:
                pass
            else:
                raise NotImplementedError(prop)
            if masses:
                pids_to_mass[pid] = sum(masses)
        return pids_to_mass, mass_type_to_mass

    def mass_properties(self, element_ids=None, mass_ids=None, reference_point=None,
                        sym_axis=None, scale=None):
        """
        Caclulates mass properties in the global system about the
        reference point.

        Parameters
        ----------
        element_ids : list[int]; (n, ) ndarray, optional
            An array of element ids.
        mass_ids : list[int]; (n, ) ndarray, optional
            An array of mass ids.
        reference_point : ndarray/str/int, optional
            type : ndarray
                An array that defines the origin of the frame.
                default = <0,0,0>.
            type : str
                'cg' is the only allowed string
            type : int
                the node id
        sym_axis : str, optional
            The axis to which the model is symmetric. If AERO cards are used, this can be left blank
            allowed_values = 'no', x', 'y', 'z', 'xy', 'yz', 'xz', 'xyz'
        scale : float, optional
            The WTMASS scaling value.
            default=None -> PARAM, WTMASS is used
            float > 0.0

        Returns
        -------
        mass : float
            The mass of the model.
        cg : ndarray
            The cg of the model as an array.
        I : ndarray
            Moment of inertia array([Ixx, Iyy, Izz, Ixy, Ixz, Iyz]).

        I = mass * centroid * centroid

        .. math:: I_{xx} = m (dy^2 + dz^2)

        .. math:: I_{yz} = -m * dy * dz

        where:

        .. math:: dx = x_{element} - x_{ref}

        .. seealso:: http://en.wikipedia.org/wiki/Moment_of_inertia#Moment_of_inertia_tensor

        .. note::
           This doesn't use the mass matrix formulation like Nastran.
           It assumes m*r^2 is the dominant term.
           If you're trying to get the mass of a single element, it
           will be wrong, but for real models will be correct.

        Example 1
        ---------
        # mass properties of entire structure
        mass, cg, I = model.mass_properties()
        Ixx, Iyy, Izz, Ixy, Ixz, Iyz = I


        Example 2
        ---------
        # mass properties of model based on Property ID
        pids = list(model.pids.keys())
        pid_eids = self.get_element_ids_dict_with_pids(pids)

        for pid, eids in sorted(iteritems(pid_eids)):
            mass, cg, I = model.mass_properties(element_ids=eids)
        """
        if reference_point is None:
            reference_point = array([0., 0., 0.])
        elif isinstance(reference_point, integer_types):
            reference_point = self.nodes[reference_point].get_position()

        elements, masses = _mass_properties_elements_init(self, element_ids, mass_ids)
        mass, cg, I = _mass_properties(
            self, elements, masses,
            reference_point=reference_point)
        mass, cg, I = _apply_mass_symmetry(self, sym_axis, scale, mass, cg, I)
        return (mass, cg, I)

    def mass_properties_no_xref(self, element_ids=None, mass_ids=None, reference_point=None,
                                sym_axis=None, scale=None):
        """
        Caclulates mass properties in the global system about the
        reference point.

        Parameters
        ----------
        element_ids : list[int]; (n, ) ndarray, optional
            An array of element ids.
        mass_ids : list[int]; (n, ) ndarray, optional
            An array of mass ids.
        reference_point : ndarray/str/int, optional
            type : ndarray
                An array that defines the origin of the frame.
                default = <0,0,0>.
            type : str
                'cg' is the only allowed string
            type : int
                the node id
        sym_axis : str, optional
            The axis to which the model is symmetric. If AERO cards are used, this can be left blank
            allowed_values = 'no', x', 'y', 'z', 'xy', 'yz', 'xz', 'xyz'
        scale : float, optional
            The WTMASS scaling value.
            default=None -> PARAM, WTMASS is used
            float > 0.0

        Returns
        -------
        mass : float
            The mass of the model.
        cg : ndarray
            The cg of the model as an array.
        I : ndarray
            Moment of inertia array([Ixx, Iyy, Izz, Ixy, Ixz, Iyz]).

        I = mass * centroid * centroid

        .. math:: I_{xx} = m (dy^2 + dz^2)

        .. math:: I_{yz} = -m * dy * dz

        where:

        .. math:: dx = x_{element} - x_{ref}

        .. seealso:: http://en.wikipedia.org/wiki/Moment_of_inertia#Moment_of_inertia_tensor

        .. note::
           This doesn't use the mass matrix formulation like Nastran.
           It assumes m*r^2 is the dominant term.
           If you're trying to get the mass of a single element, it
           will be wrong, but for real models will be correct.

        Example 1
        ---------
        # mass properties of entire structure
        mass, cg, I = model.mass_properties()
        Ixx, Iyy, Izz, Ixy, Ixz, Iyz = I


        Example 2
        ---------
        # mass properties of model based on Property ID
        pids = list(model.pids.keys())
        pid_eids = self.get_element_ids_dict_with_pids(pids)

        for pid, eids in sorted(iteritems(pid_eids)):
            mass, cg, I = model.mass_properties(element_ids=eids)
        """
        if reference_point is None:
            reference_point = array([0., 0., 0.])
        elif isinstance(reference_point, integer_types):
            reference_point = self.nodes[reference_point].get_position()

        elements, masses = _mass_properties_elements_init(self, element_ids, mass_ids)
        #nelements = len(elements) + len(masses)

        mass, cg, I = _mass_properties_no_xref(
            self, elements, masses,
            reference_point=reference_point)

        mass, cg, I = _apply_mass_symmetry(self, sym_axis, scale, mass, cg, I)
        return (mass, cg, I)

    def resolve_grids(self, cid=0):
        """
        Puts all nodes in a common coordinate system (mainly for cid testing)

        Parameters
        ----------
        cid : int; default=0
            the cid to resolve the nodes to

        .. note::

           loses association with previous coordinate systems so to go
           back requires another FEM
        """
        assert cid in self.coords, ('cannot resolve nodes to '
                                    'cid=%r b/c it doesnt exist' % cid)
        for nid, node in sorted(iteritems(self.nodes)):
            p = node.get_position_wrt(self, cid)
            node.set_position(self, p, cid)

    #def __gravity_load(self, loadcase_id):
        #"""
        #.. todo::
            #1.  resolve the load case
            #2.  grab all of the GRAV cards and combine them into one
                #GRAV vector
            #3.  run mass_properties to get the mass
            #4.  multiply by the gravity vector
        #"""

        #gravity_i = self.loads[2][0]  ## .. todo:: hardcoded
        #gi = gravity_i.N * gravity_i.scale
        #p0 = array([0., 0., 0.])  ## .. todo:: hardcoded
        #mass, cg, I = self.mass_properties(reference_point=p0, sym_axis=None)

    def sum_forces_moments_elements(self, p0, loadcase_id, eids, nids,
                                    include_grav=False, xyz_cid0=None):
        """
        Sum the forces/moments based on a list of nodes and elements.

        Parameters
        ----------
        eids : List[int]
            the list of elements to include (e.g. the loads due to a PLOAD4)
        nids : List[int]
            the list of nodes to include (e.g. the loads due to a FORCE card)
        p0 : int; (3,) ndarray
           the point to sum moments about
           type = int
               sum moments about the specified grid point
           type = (3, ) ndarray/list (e.g. [10., 20., 30]):
               the x, y, z location in the global frame
        loadcase_id : int
            the LOAD=ID to analyze
        include_grav : bool; default=False
            includes gravity in the summation (not supported)
        xyz_cid0 : None / Dict[int] = (3, ) ndarray
            the nodes in the global coordinate system

        Returns
        -------
        forces : NUMPY.NDARRAY shape=(3,)
            the forces
        moments : NUMPY.NDARRAY shape=(3,)
            the moments

        Nodal Types  : FORCE, FORCE1, FORCE2,
                       MOMENT, MOMENT1, MOMENT2,
                       PLOAD
        Element Types: PLOAD1, PLOAD2, PLOAD4, GRAV

        If you have a CQUAD4 (eid=3) with a PLOAD4 (sid=3) and a FORCE
        card (nid=5) acting on it, you can incldue the PLOAD4, but
        not the FORCE card by using:

        For just pressure:

        .. code-block:: python

          eids = [3]
          nids = []

        For just force:

        .. code-block:: python

          eids = []
          nids = [5]

        or both:

        .. code-block:: python

          eids = [3]
          nids = [5]

        .. note:: If you split the model into sections and sum the loads
                  on each section, you may not get the same result as
                  if you summed the loads on the total model.  This is
                  due to the fact that nodal loads on the boundary are
                  double/triple/etc. counted depending on how many breaks
                  you have.

        .. todo:: not done...
        """
        forces, moments = sum_forces_moments_elements(self, p0, loadcase_id, eids, nids,
                                                      include_grav=include_grav, xyz_cid0=xyz_cid0)
        return forces, moments

    def sum_forces_moments(self, p0, loadcase_id, include_grav=False, xyz_cid0=None):
        """
        Sums applied forces & moments about a reference point p0 for all
        load cases.
        Considers:
          - FORCE, FORCE1, FORCE2
          - MOMENT, MOMENT1, MOMENT2
          - PLOAD, PLOAD2, PLOAD4
          - LOAD

        Parameters
        ----------
        p0 : NUMPY.NDARRAY shape=(3,) or integer (node ID)
            the reference point
        loadcase_id : int
            the LOAD=ID to analyze
        include_grav : bool; default=False
            includes gravity in the summation (not supported)
        xyz_cid0 : None / Dict[int] = (3, ) ndarray
            the nodes in the global coordinate system

        Returns
        -------
        forces : NUMPY.NDARRAY shape=(3,)
            the forces
        moments : NUMPY.NDARRAY shape=(3,)
            the moments

        .. warning:: not full validated
        .. todo:: It's super slow for cid != 0.   We can speed this up a lot
                 if we calculate the normal, area, centroid based on
                 precomputed node locations.

        Pressure acts in the normal direction per model/real/loads.bdf and loads.f06
        """
        forces, moments = sum_forces_moments(self, p0, loadcase_id,
                                             include_grav=include_grav, xyz_cid0=xyz_cid0)
        return forces, moments

    def get_element_faces(self, element_ids=None, allow_blank_nids=True):
        """
        Gets the elements and faces that are skinned from solid elements.
        This includes internal faces, but not existing shells.

        Parameters
        ----------
        element_ids : List[int] / None
            skin a subset of element faces
            default=None -> all elements
        allow_blank_nids : bool; default=True
            allows for nids to be None

        Returns
        -------
        eid_faces : (int, List[(int, int, ...)])
           value1 : element id
           value2 : face
        """
        if element_ids is None:
            element_ids = self.element_ids

        eid_faces = []
        if allow_blank_nids:
            for eid in element_ids:
                elem = self.elements[eid]
                if elem.type in ['CTETRA', 'CPENTA', 'CHEXA', 'CPYRAM']:
                    faces = elem.faces
                    for face_id, face in iteritems(faces):
                        eid_faces.append((eid, face))
        else:
            for eid in element_ids:
                elem = self.elements[eid]
                if elem.type in ['CTETRA', 'CPENTA', 'CHEXA', 'CPYRAM']:
                    faces = elem.faces
                    for face_id, face in iteritems(faces):
                        if None in face:
                            msg = 'There is a None in the face.\n'
                            msg = 'face_id=%s face=%s\n%s' % (face_id, str(face), str(elem))
                            raise RuntimeError(msg)
                        eid_faces.append((eid, face))
        return eid_faces

    def get_solid_skin_faces(self):
        """
        Gets the elements and faces that are skinned from solid elements.
        This doesn't include internal faces or existing shells.

        Returns
        -------
        eid_set : Dict[tuple(int, int, ...)] = List[int]
           key : sorted face
           value : list of element ids with that face
        face_map : Dict[tuple(int, int, ...)] = List[int]
           key : sorted face
           value : unsorted face
        """
        eid_faces = self.get_element_faces()
        face_set = defaultdict(int)
        eid_set = defaultdict(list)
        face_map = {}
        for eid, face in eid_faces:
            #print(eid, face)
            raw_face = deepcopy(face)
            try:
                face.sort()
            except:
                print('face = %s' % str(face))
                raise
            tface = tuple(face)
            #print(tface)
            face_set[tface] += 1
            eid_set[tface].append(eid)
            face_map[tface] = raw_face

        #print('eid_set:')
        #for tface, eidset in iteritems(eid_set):
            #print(tface, eidset)

        #print('face_set:')
        #for tface, faceset in iteritems(face_set):
            #print(tface, faceset)

        #print('face_map:')
        #for tface, facemap in iteritems(face_map):
            #print(tface, facemap)

        del_faces = []
        for face, face_count in iteritems(face_set):
            if face_count == 2:
                del_faces.append(face)

        for face in del_faces:
            del face_set[face]
            del eid_set[face]
        return eid_set, face_map

    def write_skin_solid_faces(self, skin_filename,
                               write_solids=False, write_shells=True,
                               size=8, is_double=False, encoding=None):
        """
        Writes the skinned elements

        Parameters
        ----------
        skin_filename : str
            the file to write
        write_solids : bool; default=False
            write solid elements that have skinned faces
        write_shells : bool; default=False
            write newly created shell elements
            if there are shells in the model, doesn't write these

        size : int; default=8
            the field width
        is_double : bool; default=False
            double precision flag
        encoding : str; default=None -> system default
            the string encoding
        """
        if(len(self.element_ids) == 0 or len(self.material_ids) == 0 or
           len(self.property_ids) == 0):
            return
        eid_set, face_map = self.get_solid_skin_faces()
        if len(eid_set) == 0:
            return

        eid_set_to_write = set([])
        nid_set_to_write = set([])
        mid_set_to_write = set([])
        if write_solids:
            for face, eids in iteritems(eid_set):
                eid_set_to_write.update(eids)
                for eid in eids:
                    elem = self.elements[eid]
                    pid = elem.Pid()
                    prop = self.properties[pid] # PSOLID
                    mid = prop.Mid()
                    #print(prop)
                    nid_set_to_write.update(elem.node_ids)
                    mid_set_to_write.add(mid)
                    #print('added_mid (a) =', mid)
        elif write_shells:
            for face, eids in iteritems(eid_set):
                eid_set_to_write.update(eids)
                nid_set_to_write.update(face)
                for eid in eids:
                    elem = self.elements[eid]
                    pid = elem.Pid()
                    prop = self.properties[pid] # PSOLID
                    if prop.type in ['PSOLID', 'PLSOLID']:
                        mid = prop.Mid()
                    elif prop.type == 'PCOMPS':
                        mid = prop.mids[0]
                    else:
                        raise NotImplementedError(prop)
                    #except TypeError:
                        #self.log.warning('TypeError: skipping:%s' % prop)
                        #raise
                    #except AttributeError:
                        #self.log.warning('skipping:%s' % prop)
                        #continue
                    mid_set_to_write.add(mid)
                    #print('added eid=%s pid=%s mid=%s (b)' % (eid, pid, mid))
        else:
            raise RuntimeError('write_solids=False write_shells=False')

        eids_to_write = list(eid_set_to_write)
        nids_to_write = list(nid_set_to_write)
        mids_to_write = list(mid_set_to_write)

        #element_ids_to_delete = set(self.element_ids) - eids_to_write

        eid_shell = max(self.elements) + 1
        pid_shell = max(self.properties) + 1
        mid_shell = max(self.materials) + 1
        self._write_skin_solid_faces(skin_filename, face_map,
                                     nids_to_write, eids_to_write, mids_to_write, eid_set,
                                     eid_shell, pid_shell, mid_shell,
                                     write_solids=write_solids, write_shells=write_shells,
                                     size=size, is_double=is_double, encoding=encoding)

    def _write_skin_solid_faces(self, skin_filename, face_map,
                                nids_to_write, eids_to_write, mids_to_write, eid_set,
                                eid_shell, pid_shell, mid_shell,
                                write_solids=False, write_shells=True,
                                size=8, is_double=False, encoding=None):
        """
        helper method for ``write_skin_solid_faces``

        Parameters
        ----------
        skin_filename : str
            the file to write
        face_map : dict[sorted_face] : face
            sorted_face : List[int, int, int] / List[int, int, int, int]
            face : List[int, int, int] / List[int, int, int, int]

        nids_to_write : List[int, int, ...]
            list of node ids to write
        eids_to_write : List[int, int, ...]
            list of element ids to write
        mids_to_write : List[int, int, ...]
            list of material ids to write
        eid_set : ???
            ???

        eid_shell : int
            the next id to use for the shell id
        pid_shell : int
            the next id to use for the shell property
        mid_shell : int
            the next id to use for the shell material

        write_solids : bool; default=False
            write solid elements that have skinned faces
        write_shells : bool; default=True
            write shell elements
        size : int; default=8
            the field width
        is_double : bool; default=False
            double precision flag
        encoding : str; default=None -> system default
            the string encoding
        """
        encoding = self.get_encoding(encoding)
        if PY2:
            wb = 'wb'
        else:
            wb = 'w'
        with open(skin_filename, wb, encoding=encoding) as bdf_file:
            bdf_file.write('$ pyNastran: punch=True\n')
            for nid in sorted(nids_to_write):
                if nid is None:
                    continue
                node = self.nodes[nid]
                bdf_file.write(node.write_card(size=size, is_double=is_double))

            for cid, coord in iteritems(self.coords):
                if cid == 0:
                    continue
                bdf_file.write(coord.write_card(size=size, is_double=is_double))

            if write_solids:
                for eid in sorted(eids_to_write):
                    elem = self.elements[eid]
                    bdf_file.write(elem.write_card(size=size))
                for pid, prop in iteritems(self.properties):
                    bdf_file.write(prop.write_card(size=size, is_double=is_double))
                for mid in sorted(mids_to_write):
                    material = self.materials[mid]
                    bdf_file.write(material.write_card(size=size, is_double=is_double))
                del eid, pid, mid

            if write_shells:
                mids_to_write.sort()
                for imid, mid in enumerate(mids_to_write):
                    card = ['PSHELL', pid_shell + imid, mid_shell + imid, 0.1]
                    try:
                        msg = print_card_8(card)
                    except RuntimeError:
                        msg = print_card_16(card)
                    bdf_file.write(msg)

                    card = ['MAT1', mid_shell + imid, 3.e7, None, 0.3]
                    #bdf_file.write(self.materials[mid].comment)
                    try:
                        msg = print_card_8(card)
                    except RuntimeError:
                        msg = print_card_16(card)
                    bdf_file.write(msg)

                for face, eids in iteritems(eid_set):
                    face_raw = face_map[face]
                    nface = len(face)
                    #assert len(eids) == 1, eids
                    #for eid in sorted(eids):
                        #elem = self.elements[eid]
                        #print(elem)
                        #break

                    #elem = next(itervalues(self.elements)) # old
                    elem = self.elements[eids[0]]
                    #pid = next(iterkeys(self.properties))
                    pid = elem.Pid()
                    prop = self.properties[pid]
                    try:
                        mid = prop.Mid()
                    except AttributeError:
                        continue
                    #print('mids_to_write = %s' % mids_to_write)
                    #print('mids = ', self.materials.keys())
                    imid = mids_to_write.index(mid)

                    if nface == 3:
                        card = ['CTRIA3', eid_shell, pid_shell + imid] + list(face_raw)
                    elif nface == 4:
                        card = ['CQUAD4', eid_shell, pid_shell + imid] + list(face_raw)
                    elif nface == 4:
                        card = ['CQUAD4', eid_shell, pid_shell + imid] + list(face_raw)
                    elif nface == 6:
                        card = ['CTRIA6', eid_shell, pid_shell + imid] + list(face_raw)
                    elif nface == 8:
                        card = ['CQUAD8', eid_shell, pid_shell + imid] + list(face_raw)
                    else:
                        raise NotImplementedError('face=%s len(face)=%s' % (face, nface))
                    try:
                        msg = print_card_8(card)
                    except RuntimeError:
                        msg = print_card_16(card)
                    bdf_file.write(msg)
                    eid_shell += 1

                    #elem = self.elements[eid]
                    #bdf_file.write(elem.write_card(size=size))
                #for pid, prop in iteritems(self.properties):
                    #bdf_file.write(prop.write_card(size=size, is_double=is_double))
            bdf_file.write('ENDDATA\n')
        #if 0:
            #model = self.__class__.__init__()
            #model.read_bdf(skin_filename)
