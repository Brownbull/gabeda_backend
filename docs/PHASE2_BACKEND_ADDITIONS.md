# Phase 2 Backend Additions

## Overview
To complete Phase 2 frontend integration, add the following custom actions to `DataUploadViewSet` in `apps/analytics/views.py`.

## Required Changes

### File: `apps/analytics/views.py`

Add these two methods to the `DataUploadViewSet` class (after the `by_company` method, around line 144):

```python
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        Get upload status - returns upload details in same format as frontend expects
        GET /api/analytics/uploads/{id}/status/
        """
        upload = self.get_object()
        serializer = self.get_serializer(upload)
        return Response({'upload': serializer.data})

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recent uploads with optional limit
        GET /api/analytics/uploads/recent/?limit=10
        """
        limit = int(request.query_params.get('limit', 10))
        uploads = self.get_queryset()[:limit]
        serializer = self.get_serializer(uploads, many=True)
        return Response({
            'uploads': serializer.data,
            'count': len(serializer.data)
        })
```

## API Endpoints Created

These actions create the following endpoints:

1. **GET /api/analytics/uploads/{id}/status/**
   - Returns upload status and metadata
   - Used by frontend polling hook
   - Response format:
     ```json
     {
       "upload": {
         "id": "uuid",
         "file_name": "string",
         "status": "pending|processing|completed|failed",
         "uploaded_at": "datetime",
         "updated_at": "datetime",
         "error_message": "string",
         "processing_metadata": {
           "transactions_created": 609,
           "datasets_created": 0,
           "results_created": 2
         }
       }
     }
     ```

2. **GET /api/analytics/uploads/recent/?limit=10**
   - Returns recent uploads for the user's companies
   - Used by Dashboard RecentUploads component
   - Response format:
     ```json
     {
       "uploads": [
         {
           "id": "uuid",
           "file_name": "string",
           "status": "string",
           "uploaded_at": "datetime",
           "updated_at": "datetime",
           "processing_metadata": {...}
         }
       ],
       "count": 5
     }
     ```

## Testing

After adding these methods, test with:

```bash
# Get upload status
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/analytics/uploads/<upload-id>/status/

# Get recent uploads
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/analytics/uploads/recent/?limit=5
```

## Alternative: Use Existing Endpoints

If you don't want to add these custom actions, update the frontend service to use:

1. **For upload status**: Use `GET /api/analytics/uploads/{id}/` (existing retrieve endpoint)
   - Change in `src/lib/analyticsService.ts`:
     ```typescript
     async getUploadStatus(uploadId: string): Promise<UploadStatusResponse> {
       const response = await api.get<DataUpload>(
         `/analytics/uploads/${uploadId}/`  // Remove '/status'
       );
       return { upload: response.data };  // Wrap response
     }
     ```

2. **For recent uploads**: Use `GET /api/analytics/uploads/?limit=10` (existing list endpoint with pagination)
   - Change in `src/lib/analyticsService.ts`:
     ```typescript
     async getRecentUploads(limit: number = 10): Promise<RecentUploadsResponse> {
       const response = await api.get<{results: DataUpload[]}>(
         `/analytics/uploads/`,
         { params: { page_size: limit } }
       );
       return {
         uploads: response.data.results,
         count: response.data.results.length
       };
     }
     ```

Choose either approach - adding the backend custom actions is cleaner, but using existing endpoints requires no backend changes.
