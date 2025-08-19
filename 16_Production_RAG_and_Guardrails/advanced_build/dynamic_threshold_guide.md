# Dynamic Similarity Threshold Guide

This guide explains how to use the new dynamic similarity threshold functionality that allows you to change the semantic cache threshold in real-time without restarting the application.

## 🚀 New Features

### 1. **Dynamic Threshold Updates**
- Change similarity threshold at runtime via API
- No application restart required
- Immediate effect on new requests
- Validation of threshold values (0.0 to 1.0)

### 2. **Multiple Update Methods**
- **API Endpoints**: RESTful endpoints for programmatic access
- **Streamlit UI**: Interactive slider in the web interface
- **CLI Tool**: Command-line interface for quick updates
- **Demo Scripts**: Comprehensive testing and demonstration

## 📡 API Endpoints

### Get Current Threshold
```bash
GET /current_similarity_threshold
```

**Response:**
```json
{
  "current_threshold": 0.85,
  "service_threshold": 0.85
}
```

### Update Threshold
```bash
POST /update_similarity_threshold
Content-Type: application/json

{
  "threshold": 0.80
}
```

**Response:**
```json
{
  "message": "Similarity threshold updated successfully",
  "old_threshold": 0.85,
  "new_threshold": 0.80,
  "note": "Changes apply to new requests. Existing cached items remain unchanged."
}
```

## 🎛️ Streamlit Interface

The Streamlit app now includes a **Semantic Cache Settings** section in the sidebar:

- **Similarity Threshold Slider**: Adjust from 0.0 to 1.0
- **Update Threshold Button**: Apply changes immediately
- **Current Threshold Display**: Shows the active threshold
- **Real-time Updates**: Changes take effect immediately

### Usage:
1. Adjust the slider to your desired threshold
2. Click "Update Threshold" to apply changes
3. The new threshold is immediately active
4. Monitor cache performance with the new setting

## 🖥️ Command Line Interface

### CLI Tool Location
```bash
tools/threshold_cli.py
```

### Basic Usage
```bash
# View current threshold
python tools/threshold_cli.py get

# Update threshold to 0.80
python tools/threshold_cli.py set 0.80

# Use custom backend URL
python tools/threshold_cli.py set 0.75 --url http://localhost:8080
```

### CLI Help
```bash
python tools/threshold_cli.py --help
```

## 🧪 Demo Scripts

### 1. **Dynamic Threshold Demo**
```bash
python examples/dynamic_threshold_demo.py
```

This script:
- Tests multiple threshold values (0.75, 0.80, 0.85, 0.90, 0.95)
- Shows how each threshold affects cache behavior
- Demonstrates real-time threshold updates
- Provides performance insights for different settings

### 2. **Semantic Cache Demo**
```bash
python examples/semantic_cache_demo.py
```

This script:
- Tests basic semantic cache functionality
- Shows cache hit/miss behavior
- Demonstrates context overlap requirements
- Provides baseline performance metrics

## 🔧 Technical Implementation

### Backend Changes

#### 1. **AppService Class**
```python
def update_similarity_threshold(self, new_threshold: float):
    """Update the similarity threshold for the semantic cache"""
    if not 0.0 <= new_threshold <= 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0")
    
    self.sim_threshold = new_threshold
    self.semantic_cache.update_similarity_threshold(new_threshold)
    
    # Update environment variable
    os.environ['CACHE_SIM_THRESHOLD'] = str(new_threshold)
```

#### 2. **SemanticCache Class**
```python
def update_similarity_threshold(self, new_threshold: float):
    """Update the similarity threshold dynamically"""
    if not 0.0 <= new_threshold <= 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0")
    
    old_threshold = self.similarity_threshold
    self.similarity_threshold = new_threshold
    
    if self.debug:
        print(f"Updated similarity threshold from {old_threshold:.4f} to {new_threshold:.4f}")
    
    return old_threshold
```

### Frontend Changes

#### Streamlit Integration
```python
# Dynamic similarity threshold control
new_threshold = st.sidebar.slider(
    "Similarity Threshold", 
    0.0, 1.0, 
    value=float(current_threshold), 
    step=0.01,
    help="Higher values = stricter matching, fewer cache hits. Lower values = more lenient, more cache hits."
)

# Update threshold button
if st.sidebar.button("Update Threshold", key="update_threshold"):
    # API call to update threshold
    response = requests.post(
        f"{backend_url.rstrip('/')}/update_similarity_threshold",
        json={"threshold": new_threshold}
    )
```

## 📊 Threshold Guidelines

### **Low Threshold (0.70-0.80)**
- **Use Case**: High cache hit rate desired
- **Pros**: More questions will hit the cache
- **Cons**: Potentially lower quality matches
- **Best For**: Development, testing, high-traffic scenarios

### **Medium Threshold (0.80-0.90)**
- **Use Case**: Balanced approach
- **Pros**: Good balance of cache hits and quality
- **Cons**: Moderate cache hit rate
- **Best For**: Production environments, general use

### **High Threshold (0.90-0.95)**
- **Use Case**: High quality matches required
- **Pros**: Very high quality cache hits
- **Cons**: Fewer cache hits
- **Best For**: Critical applications, quality-focused scenarios

## 🔍 Monitoring and Debugging

### Enable Debug Mode
```bash
# Set environment variable
export DEBUG_CACHE=true

# Or in docker-compose.yml
environment:
  - DEBUG_CACHE=true
```

### Debug Output
When debug mode is enabled, you'll see:
- Threshold update confirmations
- Similarity scores for cache decisions
- Cache hit/miss details
- Qdrant operation logs

### Cache Statistics
```bash
curl http://localhost:8080/cache_stats
```

Monitor:
- Vector count in semantic cache
- Current threshold setting
- Cache performance metrics

## 🚨 Important Notes

### 1. **Immediate Effect**
- Threshold changes take effect immediately
- No restart required
- Changes apply to new requests only

### 2. **Existing Cache**
- Previously cached items remain unchanged
- New similarity calculations use the new threshold
- Cache hit/miss behavior changes immediately

### 3. **Validation**
- Threshold must be between 0.0 and 1.0
- Invalid values return HTTP 400 errors
- Range validation prevents invalid settings

### 4. **Persistence**
- Changes persist until next restart
- Environment variables are updated
- Service instances maintain the new threshold

## 🧪 Testing Your Threshold

### 1. **Quick Test**
```bash
# Set threshold to 0.80
python tools/threshold_cli.py set 0.80

# Test similarity
curl -X POST http://localhost:8080/test_semantic_similarity \
  -H 'Content-Type: application/json' \
  -d '{"question1":"What is this document about?","question2":"Tell me about the main topic"}'
```

### 2. **Performance Test**
```bash
# Run the dynamic threshold demo
python examples/dynamic_threshold_demo.py

# Monitor cache behavior with different thresholds
# Observe cache hit rates and response times
```

### 3. **Production Monitoring**
```bash
# Get current threshold
curl -s http://localhost:8080/current_similarity_threshold

# Monitor cache stats
curl http://localhost:8080/cache_stats

# Check application logs for debug information
docker logs session16_advanced_build
```

## 🔄 Workflow Examples

### Development Workflow
1. Start with threshold 0.85 (balanced)
2. Test with various question types
3. Lower to 0.80 if you need more cache hits
4. Raise to 0.90 if quality is insufficient
5. Monitor performance and adjust as needed

### Production Workflow
1. Set initial threshold based on requirements
2. Monitor cache hit rates and response times
3. Adjust threshold during low-traffic periods
4. Test changes with similar questions
5. Document optimal settings for your use case

### Troubleshooting Workflow
1. Check current threshold: `GET /current_similarity_threshold`
2. Enable debug mode: `DEBUG_CACHE=true`
3. Test similarity: `POST /test_semantic_similarity`
4. Monitor logs for cache decisions
5. Adjust threshold based on findings

## 🎯 Best Practices

### 1. **Start Conservative**
- Begin with threshold 0.85
- Monitor cache behavior
- Adjust gradually based on performance

### 2. **Test Thoroughly**
- Use the demo scripts
- Test with various question types
- Monitor cache hit rates

### 3. **Monitor Performance**
- Track response times
- Monitor cache hit rates
- Watch for quality degradation

### 4. **Document Changes**
- Record threshold changes
- Note performance impacts
- Document optimal settings

## 🆘 Troubleshooting

### Common Issues

#### 1. **Threshold Not Updating**
- Check API response for errors
- Verify backend logs
- Ensure service is running

#### 2. **Cache Behavior Unchanged**
- Verify threshold was updated
- Check if questions are similar enough
- Monitor debug logs

#### 3. **Invalid Threshold Values**
- Ensure value is between 0.0 and 1.0
- Check for type conversion issues
- Validate input format

### Debug Commands
```bash
# Check current threshold
curl -s http://localhost:8080/current_similarity_threshold

# View backend logs
docker logs session16_advanced_build

# Test similarity calculation
curl -X POST http://localhost:8080/test_semantic_similarity \
  -H 'Content-Type: application/json' \
  -d '{"question1":"test","question2":"test"}'
```

## 🎉 Summary

The dynamic similarity threshold feature provides:

✅ **Real-time Updates**: Change threshold without restarts  
✅ **Multiple Interfaces**: API, Streamlit, CLI, and demo scripts  
✅ **Immediate Effect**: Changes apply to new requests instantly  
✅ **Validation**: Range checking and error handling  
✅ **Monitoring**: Debug mode and statistics endpoints  
✅ **Flexibility**: Easy testing and optimization  

This feature makes your semantic cache much more flexible and allows you to optimize performance based on your specific use case and requirements.
