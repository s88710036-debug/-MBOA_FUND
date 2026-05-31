from django.urls import get_resolver
def walk_patterns(patterns, prefix=''):
    out = []
    for p in patterns:
        name = getattr(p, 'name', None)
        try:
            route = p.pattern._route
        except Exception:
            route = str(p.pattern)
        out.append(f"{prefix}{route} -> {name}")
        if hasattr(p, 'url_patterns'):
            out.extend(walk_patterns(p.url_patterns, prefix=prefix+route))
    return out

r = get_resolver()
lines = walk_patterns(r.url_patterns)
open('scripts/url_names_out.txt','w',encoding='utf-8').write('\n'.join(lines))
print('WROTE scripts/url_names_out.txt')
