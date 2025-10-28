import React, { useState, useRef } from 'react';
import {
  Upload,
  Download,
  Image as ImageIcon,
  Loader2,
  AlertCircle,
  LogOut,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../components/AuthContext';
import axios from 'axios';
import '../styles/analysis.css';

function Analysis() {
  const [selectedImage, setSelectedImage] = useState(null);
  const [pressureImage, setPressureImage] = useState(null);
  const [grayscaleImage, setGrayscaleImage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [footMetrics, setFootMetrics] = useState(null);
  const fileInputRef = useRef(null);
  const { userType, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const validateImage = (file) => {
    const validTypes = ['image/jpeg', 'image/png'];
    const maxSize = 5 * 1024 * 1024;
    if (!validTypes.includes(file.type)) {
      setError('Please upload a JPEG or PNG image');
      return false;
    }
    if (file.size > maxSize) {
      setError('Image size should be less than 5MB');
      return false;
    }
    return true;
  };

  const handleImageUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!validateImage(file)) return;

    try {
      setIsProcessing(true);
      setError(null);
      setUploadProgress(0);
      setAnalysisResult(null);
      setFootMetrics(null);
      setPressureImage(null);
      setGrayscaleImage(null);

      const reader = new FileReader();
      reader.onloadend = () => setSelectedImage(reader.result);
      reader.readAsDataURL(file);

      const formData = new FormData();
      formData.append('image', file);

      const response = await axios.post('http://localhost:5000/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        },
      });
      
      const {
        pressure_heatmap,
        contour_heatmap,
        prediction,
        confidence,
        foot_length_cm,
        foot_width_cm,
        staheli_index,
        chippaux_index,
        harris_index,
      } = response.data;

      const formatImage = (imgUrl) => {
        if (typeof imgUrl === 'string' && (imgUrl.startsWith('/') || imgUrl.startsWith('http'))) {
          return `http://localhost:5000${imgUrl}`;
        }
        return null;
      };

      setPressureImage(formatImage(pressure_heatmap));
      setGrayscaleImage(formatImage(contour_heatmap));
      setAnalysisResult({ condition: prediction, confidence });
      setFootMetrics({
        length: foot_length_cm,
        width: foot_width_cm,
        staheli_index,
        chippaux_index,
        harris_index,
      });
      setUploadProgress(100);
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Error processing image';
      setError(errorMessage);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = () => {
    if (pressureImage) {
      const link = document.createElement('a');
      link.href = pressureImage;
      link.download = `foot-pressure-analysis-${new Date().toISOString()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const getSuggestions = (condition) => {
    switch (condition) {
      case 'Pes_Planus':
        return [
          'Use arch supports or custom orthotics.',
          'Strengthen foot and ankle muscles with toe curls and heel raises.',
          'Avoid prolonged standing or walking on hard surfaces.',
          'Consider physical therapy if pain persists.',
        ];
      case 'Pes_Cavus':
        return [
          'Use cushioned insoles or supportive shoes.',
          'Stretch tight calf and foot muscles regularly.',
          'Limit high-impact activities like running if painful.',
          'Consult a specialist if there’s frequent ankle sprain.',
        ];
      case 'Normal_Arch':
        return [
          'Maintain good posture and foot hygiene.',
          'Wear well-fitted and supportive footwear.',
          'Do occasional arch and ankle strengthening exercises.',
          'No corrective action needed unless discomfort arises.',
        ];
      default:
        return ['No suggestions available.'];
    }
  };

  return (
    <div className="analysis-container">
      <header className="analysis-header">
        <div className="header-content">
          <div className="header-left">
            <div className="logo-icon">
              <ImageIcon className="icon" />
            </div>
            <div>
              <h1>Foot Pressure Analysis</h1>
              <p>Logged in as {userType === 'doctor' ? 'Doctor' : 'Patient'}</p>
            </div>
          </div>
          <button onClick={handleLogout} className="logout-button">
            <LogOut className="logout-icon" />
            Logout
          </button>
        </div>
      </header>

      <main className="analysis-main">
        <div className="analysis-card">
          <div className="upload-section">
            <div className="upload-container">
              <label htmlFor="image-upload" className="upload-label">
                <div className="upload-content">
                  {isProcessing ? (
                    <>
                      <div className="upload-progress">
                        <div className="progress-bar" style={{ width: `${uploadProgress}%` }}></div>
                      </div>
                      <p className="upload-text">Uploading: {uploadProgress}%</p>
                    </>
                  ) : (
                    <>
                      <div className="upload-icon-container">
                        <Upload className="upload-icon" />
                      </div>
                      <p className="upload-text">
                        <span>Click to upload</span> or drag and drop
                      </p>
                      <p className="upload-subtext">PNG or JPEG (Max 5MB)</p>
                    </>
                  )}
                </div>
                <input
                  id="image-upload"
                  type="file"
                  className="upload-input"
                  accept="image/jpeg,image/png"
                  onChange={handleImageUpload}
                  ref={fileInputRef}
                  disabled={isProcessing}
                />
              </label>
            </div>
          </div>

          {error && (
            <div className="error-message">
              <AlertCircle className="error-icon" />
              <p>{error}</p>
            </div>
          )}

          <div className="image-grid">
            <div className="image-preview">
              <h2>Original Scan</h2>
              <div className="image-container">
                {selectedImage ? (
                  <img src={selectedImage} alt="Original foot scan" className="preview-image" />
                ) : (
                  <div className="empty-state">No image uploaded</div>
                )}
              </div>
            </div>

            <div className="image-preview">
              <h2>Pressure Image</h2>
              <div className="image-container">
                {isProcessing ? (
                  <div className="loading-state">
                    <Loader2 className="loading-icon" />
                    <p>Processing image...</p>
                  </div>
                ) : pressureImage ? (
                  <img src={pressureImage} alt="Pressure image" className="preview-image" />
                ) : (
                  <div className="empty-state">No pressure image available</div>
                )}
              </div>
            </div>

            <div className="image-preview">
              <h2>Contour Image</h2>
              <div className="image-container">
                {isProcessing ? (
                  <div className="loading-state">
                    <Loader2 className="loading-icon" />
                    <p>Processing image...</p>
                  </div>
                ) : grayscaleImage ? (
                  <img src={grayscaleImage} alt="Grayscale image" className="preview-image" />
                ) : (
                  <div className="empty-state">No grayscale image available</div>
                )}
              </div>
            </div>
          </div>

          {analysisResult && (
            <div className="analysis-result">
              <h2>Analysis Result</h2>
              <p><strong>Condition: </strong>{analysisResult.condition}</p>
              {footMetrics && (
                <div className="foot-metrics">
                  <h3>Foot Metrics</h3>
                  <p><strong>Length:</strong> {footMetrics.length} cm</p>
                  <p><strong>Width:</strong> {footMetrics.width} cm</p>
                  <p><strong>Staheli Index:</strong> {footMetrics.staheli_index}</p>
                  <p><strong>Chippaux Index:</strong> {footMetrics.chippaux_index/100}</p>
                  <p><strong>Harris Index:</strong> {footMetrics.harris_index}</p>
                </div>
              )}

              <h3>Recommendations</h3>
              <ul className="suggestion-list">
                {getSuggestions(analysisResult.condition).map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>

              <button className="download-button" onClick={handleDownload}>
                <Download className="download-icon" /> Download Pressure Image
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default Analysis;
