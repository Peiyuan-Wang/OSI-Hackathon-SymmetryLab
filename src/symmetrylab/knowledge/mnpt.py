"""Public L10 MnPt starting references (Neel axis and spin transport), reviewed 2026-10-22.

A starting packet only; live runs must still search journals and arXiv for the actual question.
"""
from copy import deepcopy

PACKET = [
    {'provider':'Curated primary source','record_id':'10.1103/PhysRevB.107.064412',
     'url':'https://schleife.matse.illinois.edu/wp-content/publications-data/pdf/PhysRevB.107.064412.pdf',
     'fields':{'title':'Phonon, electron, and magnon excitations in antiferromagnetic L10-type MnPt',
               'note':'The reported chemical structure is tetragonal P4/mmm (No. 123). The work models antiferromagnetic excitations; its assumed magnetic state is not an assignment to a new sample.'},
     'scope':'Curated published model context; magnetic basis and sample applicability need checking'},
    {'provider':'Curated primary source','record_id':'10.2320/matertrans.47.2',
     'url':'https://www.jstage.jst.go.jp/article/matertrans/47/1/47_1_2/_article',
     'fields':{'title':'Electrical and Magnetic Properties, and Electronic Structures of Pseudo-Gap-Type Antiferromagnetic L10-Type MnPt Alloys',
               'note':'For the equiatomic composition, the reported calculation favors moments parallel to c and cites neutron results. Composition dependence is explicitly studied.'},
     'scope':'Published abstract; not a universal easy-axis statement'},
    {'provider':'Curated primary source','record_id':'10.1103/PhysRevB.104.144403',
     'url':'https://journals.aps.org/prb/abstract/10.1103/PhysRevB.104.144403',
     'fields':{'title':'Ferroelectric control of the Neel vector in antiferromagnetic films',
               'note':'First-principles MnPt/BaTiO3 calculations predict different anisotropies for Pt-O and Mn-O interfaces, with thickness and polarization dependence.'},
     'scope':'Theoretical prediction for specific interfaces; no evidence that a user sample has these conditions'},
    {'provider':'Curated primary source','record_id':'1903.00413',
     'url':'https://arxiv.org/abs/1903.00413',
     'fields':{'title':'Strain control of the Neel vector in Mn-based antiferromagnets',
               'note':'First-principles work studies strain-induced reorientation. Treat strain and relaxation as sample conditions, not a known measurement.'},
     'scope':'Abstract-level theoretical context'},
    {'provider':'Curated primary source','record_id':'10.48550/arXiv.2510.04184',
     'url':'https://arxiv.org/abs/2510.04184',
     'fields':{'title':'Longitudinal transport spin polarization of spin degenerate antiferromagnets',
               'note':'Magnetic-point-group analysis and DFT: PT-symmetric (spin-degenerate) antiferromagnets such as L10-MnPt can still carry longitudinal spin currents through spin-orbit coupling, with spin conductivity comparable to PT-broken antiferromagnets. Relevant to whether MnPt can supply the spin polarization that TMR requires; it does not report a measured MnPt junction TMR.'},
     'scope':'arXiv preprint (2025), abstract level; theoretical spin conductivity, not a tunnel-junction measurement'}]


def mnpt_packet():
    return {'status':'curated_reference_packet','reviewed_on':'2026-10-22','records':deepcopy(PACKET),
            'sample_assignment':'unresolved','chemical_space_group_reference':'P4/mmm (123)',
            'missing':['Sample form, substrate, thickness, strain and chemical order',
                       'Temperature, composition, magnetic propagation vector and domain populations',
                       'Sample-specific magnetic structure, MSG/SSG and coordinate convention',
                       'Instrument access, detectable signal, geometry and reciprocal basis']}
