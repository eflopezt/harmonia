"""
Vista del organigrama interactivo con exportación PDF.
"""
import json
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render
from ..models import Area, Personal

solo_admin = user_passes_test(lambda u: u.is_superuser, login_url='login')


@login_required
@solo_admin
def organigrama_view(request):
    """Renderiza la página del organigrama interactivo."""
    areas = Area.objects.filter(activa=True).order_by('nombre')
    return render(request, 'personal/organigrama.html', {
        'titulo': 'Organigrama',
        'areas': areas,
    })


@login_required
@solo_admin
def organigrama_data(request):
    """
    API JSON para el organigrama. Construye la jerarquía:
    1. Si Personal.reporta_a está definido, usa esa relación
    2. Si no, infiere: Personal → jefe de su Área → nodo raíz
    """
    area_id = request.GET.get('area')  # Filtro opcional por área

    qs = Personal.objects.filter(estado='Activo').select_related(
        'subarea__area', 'reporta_a'
    )
    if area_id:
        qs = qs.filter(subarea__area_id=area_id)

    # Construir mapa de jefes de área
    areas = Area.objects.filter(activa=True).select_related('jefe_area')
    jefe_area_map = {}  # area_id -> personal_id del jefe
    for a in areas:
        if a.jefe_area_id:
            jefe_area_map[a.id] = a.jefe_area_id

    nodes = []
    ids_incluidos = set()

    for p in qs:
        node = {
            'id': str(p.id),
            'parentId': '',
            'name': p.apellidos_nombres or '',
            'position': p.cargo or '',
            'area': p.subarea.area.nombre if p.subarea and p.subarea.area else '',
            'subarea': p.subarea.nombre if p.subarea else '',
            'dni': p.nro_doc or '',
            'grupo': p.grupo_tareo or '',
            'email': p.correo_personal or '',
            'email_corp': p.correo_corporativo or '',
            'celular': p.celular or '',
            'estado': p.estado,
            'es_jefe': False,
        }

        # Determinar parentId
        if p.reporta_a_id:
            node['parentId'] = str(p.reporta_a_id)
        elif p.subarea and p.subarea.area_id in jefe_area_map:
            jefe_id = jefe_area_map[p.subarea.area_id]
            if jefe_id != p.id:  # No auto-referencia
                node['parentId'] = str(jefe_id)
            # Si es el jefe del área, su parent será '' (raíz) o un nodo superior

        # Marcar si es jefe de área
        if p.subarea and p.subarea.area_id in jefe_area_map:
            if jefe_area_map[p.subarea.area_id] == p.id:
                node['es_jefe'] = True

        nodes.append(node)
        ids_incluidos.add(p.id)

    # Intentar incluir padres referenciados que faltan
    parent_ids_faltantes = set()
    for n in nodes:
        if n['parentId']:
            try:
                pid = int(n['parentId'])
                if pid not in ids_incluidos:
                    parent_ids_faltantes.add(pid)
            except (ValueError, TypeError):
                pass

    if parent_ids_faltantes:
        for p in Personal.objects.filter(id__in=parent_ids_faltantes, estado='Activo'):
            nodes.append({
                'id': str(p.id),
                'parentId': '',
                'name': p.apellidos_nombres or '',
                'position': p.cargo or '',
                'area': p.subarea.area.nombre if p.subarea and p.subarea.area else '',
                'subarea': p.subarea.nombre if p.subarea else '',
                'dni': p.nro_doc or '',
                'grupo': p.grupo_tareo or '',
                'email': p.correo_personal or '',
                'email_corp': p.correo_corporativo or '',
                'celular': p.celular or '',
                'estado': p.estado,
                'es_jefe': True,
            })
            ids_incluidos.add(p.id)

    # ── Nodo raiz virtual: la empresa ──
    # d3-org-chart requiere exactamente UN nodo raiz (parentId='')
    # Sanitizar: si un parentId apunta a un nodo que NO existe en el set, limpiar
    all_ids = {n['id'] for n in nodes}
    for n in nodes:
        if n['parentId'] and n['parentId'] not in all_ids:
            n['parentId'] = ''  # se reasignara al root abajo

    root_id = '_root'
    root_node = {
        'id': root_id,
        'parentId': '',
        'name': 'ANDES MINING S.A.C.',
        'position': 'Empresa',
        'area': '',
        'subarea': '',
        'dni': '',
        'grupo': '',
        'email': '',
        'email_corp': '',
        'celular': '',
        'estado': 'Activo',
        'es_jefe': False,
        '_isRoot': True,
    }
    for n in nodes:
        if not n['parentId']:
            n['parentId'] = root_id
    nodes.insert(0, root_node)

    # Ordenar: STAFF primero, luego RCO, luego otros (por parentId agrupado)
    def _sort_key(n):
        g = (n.get('grupo') or '').upper()
        if g == 'STAFF':
            return (0, n.get('name', ''))
        elif g == 'RCO':
            return (1, n.get('name', ''))
        return (2, n.get('name', ''))

    # Agrupar por parentId, ordenar dentro de cada grupo, reconstruir
    from collections import OrderedDict
    by_parent = OrderedDict()
    for n in nodes:
        pid = n['parentId']
        by_parent.setdefault(pid, []).append(n)
    sorted_nodes = []
    # Root node first (parentId='')
    for pid, children in by_parent.items():
        children.sort(key=_sort_key)
        sorted_nodes.extend(children)

    return JsonResponse(sorted_nodes, safe=False)


@login_required
@solo_admin
def organigrama_update_parent(request):
    """API para actualizar el campo reporta_a de un empleado (drag & drop o form)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requerido'}, status=405)

    import json as _json
    try:
        data = _json.loads(request.body)
        personal_id = int(data['personal_id'])
        parent_id = data.get('parent_id')  # None para hacer raíz

        p = Personal.objects.get(id=personal_id)
        if parent_id:
            parent = Personal.objects.get(id=int(parent_id))
            # Evitar ciclos
            current = parent
            while current.reporta_a_id:
                if current.reporta_a_id == personal_id:
                    return JsonResponse({'error': 'Ciclo detectado'}, status=400)
                current = current.reporta_a
            p.reporta_a = parent
        else:
            p.reporta_a = None
        p.save(update_fields=['reporta_a'])
        return JsonResponse({'ok': True})
    except (Personal.DoesNotExist, KeyError, ValueError) as e:
        return JsonResponse({'error': str(e)}, status=400)
