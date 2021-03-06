from matplotlib.backends import qt_compat

if qt_compat.QT_API in ['PyQt4', 'PySide']:
    import matplotlib.backends.backend_qt4agg as matplotlib_backend
    #from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
elif qt_compat.QT_API == 'PyQt5':
    import matplotlib.backends.backend_qt5agg as matplotlib_backend
    #from vtk.qt5.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
else:
    raise NotImplementedError(qt_compat.QT_API)
