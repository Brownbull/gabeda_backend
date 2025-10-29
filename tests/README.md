# GabeDA Backend - Test Suite

Comprehensive API test suite for the GabeDA Backend with TDD approach for continuous regression testing.

## Test Structure

```
tests/
├── conftest.py                  # Shared pytest fixtures
├── pytest.ini                   # Pytest configuration
├── test_authentication.py       # Authentication API tests (15 tests)
├── test_companies.py            # Company management API tests (28 tests)
├── test_analytics.py            # Analytics API tests (21 tests)
└── test_api.py                  # Integration test (manual script)
```

## Test Coverage

**Total Tests: 64**
- ✅ **Passing: 45 tests** (70%)
- ⏳ **Failing: 15 tests** (mostly pagination issues)
- ❌ **Errors: 1 test** (fixture conflict)
- 🟡 **Warnings: 3** (Django deprecation)

### By Category

**Authentication Tests (15 tests) - 14 passing**
- User registration (5 tests)
- User login (4 tests)
- Token refresh (2 tests)
- User profile (4 tests)

**Company Management Tests (28 tests) - 20 passing**
- Company creation (4 tests)
- Company list (4 tests)
- Company detail (2 tests)
- Company update (2 tests)
- Company delete (2 tests)
- Company members (7 tests)
- Memberships (2 tests)

**Analytics Tests (21 tests) - 11 passing**
- CSV upload (6 tests)
- Data upload list (4 tests)
- Transactions (3 tests)
- Datasets (2 tests)
- Analytics results (6 tests)

## Running Tests

### All Tests

```bash
cd C:\Projects\play\gabeda_backend
benv\Scripts\activate
pytest tests/ -v
```

### By Category (using markers)

```bash
# Authentication tests only
pytest tests/ -m auth -v

# Company tests only
pytest tests/ -m companies -v

# Analytics tests only
pytest tests/ -m analytics -v
```

### Specific Test File

```bash
pytest tests/test_authentication.py -v
pytest tests/test_companies.py -v
pytest tests/test_analytics.py -v
```

### With Coverage Report

```bash
pytest tests/ --cov=apps --cov-report=html
# Open: htmlcov/index.html
```

### Run Failing Tests Only

```bash
pytest tests/ --lf -v
```

## Test Fixtures

### User Fixtures

- `user` - Create a test user
- `admin_user` - Create an admin user
- `create_user` - Factory to create users with custom data
- `authenticated_client` - API client authenticated with test user

### Company Fixtures

- `company` - Create a test company
- `company_with_admin` - Company with user as admin member
- `company_with_analyst` - Company with user as analyst member
- `create_company` - Factory to create companies with custom data
- `company_data` - Sample company creation data

### Analytics Fixtures

- `csv_file` - Sample CSV file for upload testing
- `invalid_csv_file` - Non-CSV file for validation testing
- `empty_csv_file` - Empty file for validation testing
- `data_upload` - Test data upload record
- `transaction` - Test transaction record
- `dataset` - Test dataset record
- `kpi_result` - Test KPI analytics result
- `admin_only_result` - Admin-only analytics result

### Auth Fixtures

- `api_client` - DRF API client
- `get_tokens` - Get JWT tokens for a user
- `user_data` - Sample user registration data

## Test Patterns

### Testing Authentication

```python
def test_login_success(self, api_client, user):
    """Test successful login returns JWT tokens"""
    response = api_client.post('/api/accounts/auth/login/', {
        'email': user.email,
        'password': 'password123'
    })

    assert response.status_code == status.HTTP_200_OK
    assert 'access' in response.data
    assert 'refresh' in response.data
```

### Testing Permissions

```python
def test_upload_csv_non_member(
    self, authenticated_client, create_company, create_user, csv_file
):
    """Test non-member cannot upload CSV"""
    other_user = create_user(email='other@example.com')
    other_company = create_company(created_by=other_user)

    response = authenticated_client.post(
        f'/api/analytics/companies/{other_company.id}/upload/',
        {'file': csv_file},
        format='multipart'
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
```

### Testing File Uploads

```python
def test_upload_csv_success(self, authenticated_client, company_with_admin, csv_file):
    """Test successful CSV upload"""
    response = authenticated_client.post(
        f'/api/analytics/companies/{company_with_admin.id}/upload/',
        {'file': csv_file},
        format='multipart'
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert 'upload' in response.data
```

### Testing Role-Based Access

```python
def test_list_results_role_filtering_analyst(
    self, api_client, create_user, company_with_analyst, kpi_result, admin_only_result
):
    """Test analyst doesn't see admin-only results"""
    analyst_user = create_user(email='analyst@example.com')
    api_client.force_authenticate(user=analyst_user)

    response = api_client.get('/api/analytics/results/')

    result_ids = [r['id'] for r in response.data]
    assert str(kpi_result.id) in result_ids
    assert str(admin_only_result.id) not in result_ids
```

## Known Issues

### Pagination

DRF's pagination returns `{'results': [...]}` instead of `[...]` for list endpoints. Some tests expect the list format.

**Fix**: Update list tests to handle pagination:
```python
# Before
assert len(response.data) >= 1

# After
results = response.data.get('results', response.data)
assert len(results) >= 1
```

### Test Isolation

Some tests may have fixture conflicts due to `unique_together` constraints. Use `--reuse-db` flag to speed up tests and avoid recreating database between runs.

### Windows Path Issues

File upload tests create files in `media/` folder. Ensure proper cleanup if needed.

## TDD Workflow

1. **Write failing test** - Define expected behavior
2. **Run test** - Verify it fails
3. **Implement feature** - Write minimal code to pass
4. **Run test** - Verify it passes
5. **Refactor** - Clean up code
6. **Commit** - Save working state

## Adding New Tests

### 1. Create Test File

```python
"""
Test suite for new feature
"""
import pytest
from rest_framework import status

pytestmark = [pytest.mark.feature, pytest.mark.django_db]


class TestNewFeature:
    """Test new feature endpoint"""

    def test_feature_success(self, authenticated_client):
        """Test successful feature usage"""
        response = authenticated_client.post('/api/feature/', {...})

        assert response.status_code == status.HTTP_201_CREATED
```

### 2. Add Fixtures (if needed)

In `conftest.py`:
```python
@pytest.fixture
def feature_data():
    """Sample feature data"""
    return {...}
```

### 3. Run New Tests

```bash
pytest tests/test_new_feature.py -v
```

### 4. Update This README

Add test count and description to coverage section.

## Continuous Integration

Tests should be run:
- Before committing code
- Before creating pull requests
- In CI/CD pipeline (when configured)

## Test Data

Test data is created using fixtures and factories. No static test data files needed.

CSV test data is generated in-memory:
```python
@pytest.fixture
def csv_file():
    csv_content = b"""trans_id,fecha,producto,glosa,cantidad,total
1,2025-01-15,PROD001,Product 1,10,1000"""
    return SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
```

## Best Practices

1. **Use descriptive test names** - Test name should describe what is being tested
2. **One assertion per test** - Keep tests focused (flexible rule)
3. **Use fixtures** - Avoid duplicating setup code
4. **Test edge cases** - Not just happy paths
5. **Keep tests fast** - Use `--reuse-db` for development
6. **Clean up after tests** - Use fixtures with proper teardown
7. **Test permissions** - Verify authentication and authorization
8. **Test validation** - Check error cases and bad input

## Next Steps

- [ ] Fix pagination issues in list endpoint tests
- [ ] Add integration tests for full CSV upload → analytics flow
- [ ] Add performance tests for large CSV uploads
- [ ] Add tests for Celery tasks (when implemented)
- [ ] Achieve 90%+ code coverage
- [ ] Set up CI/CD pipeline with automated testing

---

Last Updated: 2025-10-29
Test Count: 64 (45 passing, 15 failing, 1 error, 3 warnings)
