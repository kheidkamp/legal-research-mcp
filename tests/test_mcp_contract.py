import ast
import asyncio
from copy import deepcopy
from pathlib import Path


def _get_tool_function(name: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(Path('mcp_server.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f'{name} not found')


def test_official_document_tool_has_simple_required_string_contract():
    node = _get_tool_function('get_official_document_text')
    assert [arg.arg for arg in node.args.args] == ['document_ref', 'locator', 'query']
    assert node.args.defaults == []
    assert node.args.kwonlyargs == []
    for arg in node.args.args:
        assert isinstance(arg.annotation, ast.Name)
        assert arg.annotation.id == 'str'


def test_official_document_tool_has_no_nullable_union_or_public_tuning_params():
    node = _get_tool_function('get_official_document_text')
    signature_node = ast.FunctionDef(
        name=node.name,
        args=node.args,
        body=[ast.Pass()],
        decorator_list=[],
        returns=node.returns,
        type_comment=None,
    )
    ast.fix_missing_locations(signature_node)
    signature = ast.unparse(signature_node)
    forbidden = ['str | None', 'url:', 'document_id:', 'max_passages', 'context_chars']
    for value in forbidden:
        assert value not in signature


class _FakeService:
    def __init__(self):
        self.calls = []

    async def get_official_document_text(self, **kwargs):
        self.calls.append(kwargs)
        return {'status': 'ok'}


def _load_public_tool_without_mcp(fake_service):
    node = deepcopy(_get_tool_function('get_official_document_text'))
    node.decorator_list = []
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {'service': fake_service}
    exec(compile(module, 'mcp_server.py', 'exec'), namespace)
    return namespace['get_official_document_text']


def test_public_tool_routes_document_id_internally():
    service = _FakeService()
    tool = _load_public_tool_without_mcp(service)
    result = asyncio.run(tool(' BR-Drs. 5/26 ', ' Artikel 30 Nummer 1 ', ' § 8b Absatz 6 Satz 2 '))
    assert result == {'status': 'ok'}
    assert service.calls == [{
        'document_id': 'BR-Drs. 5/26',
        'locator': 'Artikel 30 Nummer 1',
        'query': '§ 8b Absatz 6 Satz 2',
    }]


def test_public_tool_routes_https_url_internally():
    service = _FakeService()
    tool = _load_public_tool_without_mcp(service)
    url = 'https://dserver.bundestag.de/brd/2026/0005-26.pdf'
    asyncio.run(tool(url, 'Artikel 30 Nummer 1', '§ 8b Absatz 6 Satz 2'))
    assert service.calls == [{
        'url': url,
        'locator': 'Artikel 30 Nummer 1',
        'query': '§ 8b Absatz 6 Satz 2',
    }]
