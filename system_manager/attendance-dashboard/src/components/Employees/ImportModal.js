import React, { useState } from 'react';
import {
  Modal,
  Upload,
  Button,
  Alert,
  Progress,
  Typography,
  Space,
  message,
  List
} from 'antd';
import {
  InboxOutlined,
  DownloadOutlined,
  UploadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { employeeAPI } from '../../services/api';

const { Title, Text } = Typography;
const { Dragger } = Upload;

const ImportModal = ({ visible, onCancel, onSuccess }) => {
  const [uploading, setUploading] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [fileList, setFileList] = useState([]);

  const handleDownloadTemplate = async () => {
    try {
      const response = await employeeAPI.downloadTemplate();
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'mau_danh_sach_nhan_vien.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      message.success('Tải mẫu file thành công');
    } catch (error) {
      message.error('Không thể tải mẫu file');
    }
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.error('Vui lòng chọn file CSV');
      return;
    }

    try {
      setUploading(true);
      const file = fileList[0];

      // Read file content and remove BOM if exists
      const fileContent = await readFileWithoutBOM(file.originFileObj);

      // Create new file without BOM
      const cleanFile = new File([fileContent], file.name, {
        type: 'text/csv',
        lastModified: file.originFileObj.lastModified
      });

      const response = await employeeAPI.importCSV(cleanFile);

      setImportResult(response.data);

      if (response.data.success) {
        message.success('Import thành công!');
        if (response.data.data.imported > 0) {
          onSuccess?.();
        }
      }
    } catch (error) {
      if (error.response?.data) {
        setImportResult(error.response.data);
      } else {
        message.error('Lỗi import file');
      }
    } finally {
      setUploading(false);
    }
  };

  // Helper function to read file and remove BOM
  const readFileWithoutBOM = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (event) => {
        try {
          let content = event.target.result;

          // Remove BOM if exists
          // BOM for UTF-8 is EF BB BF (239 187 191 in decimal)
          // BOM for UTF-16 is FF FE or FE FF
          if (content.charCodeAt(0) === 0xFEFF) {
            content = content.slice(1);
          }

          // Also handle UTF-8 BOM in string format
          if (content.startsWith('\uFEFF')) {
            content = content.slice(1);
          }

          resolve(content);
        } catch (error) {
          reject(error);
        }
      };

      reader.onerror = () => {
        reject(new Error('Failed to read file'));
      };

      reader.readAsText(file, 'utf-8');
    });
  };

  const uploadProps = {
    accept: '.csv',
    multiple: false,
    fileList,
    beforeUpload: (file) => {
      const isCSV = file.type === 'text/csv' || file.name.endsWith('.csv');
      if (!isCSV) {
        message.error('Chỉ chấp nhận file CSV!');
        return false;
      }
      const isLt5M = file.size / 1024 / 1024 < 5;
      if (!isLt5M) {
        message.error('File phải nhỏ hơn 5MB!');
        return false;
      }
      return false; // Prevent auto upload
    },
    onChange: (info) => {
      setFileList(info.fileList);
      setImportResult(null);
    },
    onRemove: () => {
      setFileList([]);
      setImportResult(null);
    }
  };

  const handleModalClose = () => {
    setFileList([]);
    setImportResult(null);
    onCancel();
  };

  return (
    <Modal
      title="Import danh sách nhân viên"
      open={visible}
      onCancel={handleModalClose}
      width={600}
      footer={[
        <Button key="cancel" onClick={handleModalClose}>
          Đóng
        </Button>,
        <Button
          key="upload"
          type="primary"
          loading={uploading}
          onClick={handleUpload}
          disabled={fileList.length === 0}
          icon={<UploadOutlined />}
        >
          Import
        </Button>
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Download Template */}
        <div>
          <Title level={5}>1. Tải file mẫu</Title>
          <Text type="secondary">
            File CSV cần có các cột: <br/>
            • <strong>Mã nhân viên</strong> (bắt buộc) <br/>
            • <strong>Họ và tên</strong> (bắt buộc) <br/>
            • <strong>Chức vụ</strong> (bắt buộc): "Nhân viên" hoặc "Giảng viên" <br/>
            • <strong>Lương/giờ (VNĐ)</strong> (bắt buộc) <br/>
            • <strong>Giờ làm việc tiêu chuẩn</strong> (tùy chọn, mặc định: 8.0) <br/>
            • <strong>Loại lịch</strong> (tùy chọn): "fixed", "flexible", hoặc "shift" <br/>
            <br/>
            <Text type="warning">
              <strong>Lưu ý:</strong> Lịch làm việc chi tiết cần thiết lập sau khi import.
            </Text>
          </Text>
          <br />
          <Button
            icon={<DownloadOutlined />}
            onClick={handleDownloadTemplate}
            style={{ marginTop: 8 }}
          >
            Tải file mẫu
          </Button>
        </div>

        {/* Upload File */}
        <div>
          <Title level={5}>2. Chọn file CSV</Title>
          <Dragger {...uploadProps}>
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">
              Kéo thả file CSV vào đây hoặc click để chọn
            </p>
            <p className="ant-upload-hint">
              Chỉ chấp nhận file .csv, tối đa 5MB
            </p>
          </Dragger>
        </div>

        {/* Import Result */}
        {importResult && (
          <div>
            <Title level={5}>3. Kết quả import</Title>

            {importResult.success ? (
              <Alert
                message="Import thành công!"
                type="success"
                showIcon
                icon={<CheckCircleOutlined />}
                description={
                  <div>
                    <p>Đã import {importResult.data.imported} nhân viên mới</p>
                    {importResult.data.duplicates > 0 && (
                      <p>Bỏ qua {importResult.data.duplicates} nhân viên đã tồn tại</p>
                    )}
                  </div>
                }
              />
            ) : (
              <Alert
                message="Import thất bại!"
                type="error"
                showIcon
                icon={<ExclamationCircleOutlined />}
                description={
                  <div>
                    <p>{importResult.message}</p>
                    {importResult.errors && importResult.errors.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <Text strong>Chi tiết lỗi:</Text>
                        <List
                          size="small"
                          dataSource={importResult.errors.slice(0, 5)}
                          renderItem={(error) => (
                            <List.Item>
                              <Text type="danger" style={{ fontSize: '12px' }}>
                                {error}
                              </Text>
                            </List.Item>
                          )}
                        />
                        {importResult.errors.length > 5 && (
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            ... và {importResult.errors.length - 5} lỗi khác
                          </Text>
                        )}
                      </div>
                    )}
                  </div>
                }
              />
            )}

            {importResult.data && (
              <div style={{ marginTop: 12 }}>
                <Progress
                  percent={Math.round((importResult.data.imported / importResult.data.total_rows) * 100)}
                  status={importResult.success ? 'success' : 'exception'}
                  format={() => `${importResult.data.imported}/${importResult.data.total_rows}`}
                />
              </div>
            )}
          </div>
        )}
      </Space>
    </Modal>
  );
};

export default ImportModal;