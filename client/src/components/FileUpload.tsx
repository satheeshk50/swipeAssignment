import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-toastify';
import { Upload, FileText, Loader2, CheckCircle2 } from 'lucide-react';
import {
    isValidFileType,
    extractFromFiles,
    normalizeExtractedData,
    ACCEPTED_FILE_TYPES,
} from '../services/aiService';
import { useAppDispatch } from '../store/hooks';
import { addInvoices } from '../store/invoicesSlice';
import { addProducts } from '../store/productsSlice';
import { addCustomers } from '../store/customersSlice';

const FileUpload = () => {
    const dispatch = useAppDispatch();
    const [isProcessing, setIsProcessing] = useState(false);
    const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

    const onDrop = useCallback(
        async (acceptedFiles: File[]) => {
            const validFiles: File[] = [];

            // 1. Validate all files first
            for (const file of acceptedFiles) {
                if (isValidFileType(file)) {
                    validFiles.push(file);
                } else {
                    toast.error(
                        `Invalid file type: "${file.name}". Please upload PDF, Excel, or Image.`
                    );
                }
            }

            if (validFiles.length === 0) return;

            setIsProcessing(true);

            try {
                toast.info(`Processing ${validFiles.length} file(s)...`, {
                    autoClose: 3000,
                });

                // 2. Send batch request
                const rawData = await extractFromFiles(validFiles);
                const normalized = normalizeExtractedData(rawData);

                // 3. Update Store
                dispatch(addInvoices(normalized.invoices));
                dispatch(addProducts(normalized.products));
                dispatch(addCustomers(normalized.customers));

                setUploadedFiles((prev) => [...prev, ...validFiles.map((f) => f.name)]);

                // 4. Show aggregated result
                const totalWarnings = [
                    ...normalized.invoices,
                    ...normalized.products,
                    ...normalized.customers,
                ].reduce((sum, item) => sum + item.warnings.length, 0);

                if (totalWarnings > 0) {
                    toast.warning(
                        `Extracted data with ${totalWarnings} warning(s). Review flagged cells.`
                    );
                } else {
                    toast.success(`Successfully extracted data from ${validFiles.length} file(s)!`);
                }
            } catch (err) {
                const message =
                    err instanceof Error ? err.message : 'Unknown error occurred';
                toast.error(`Failed to process files: ${message}`);
            } finally {
                setIsProcessing(false);
            }
        },
        [dispatch]
    );

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: ACCEPTED_FILE_TYPES,
        disabled: isProcessing,
        multiple: true,
    });

    return (
        <div className="file-upload-section">
            <div
                {...getRootProps()}
                className={`dropzone ${isDragActive ? 'dropzone--active' : ''} ${isProcessing ? 'dropzone--disabled' : ''
                    }`}
            >
                <input {...getInputProps()} />
                <div className="dropzone__content">
                    {isProcessing ? (
                        <>
                            <Loader2 className="dropzone__icon dropzone__icon--spin" size={48} />
                            <p className="dropzone__title">Processing file...</p>
                            <p className="dropzone__subtitle">
                                AI is extracting invoice data
                            </p>
                        </>
                    ) : isDragActive ? (
                        <>
                            <Upload className="dropzone__icon dropzone__icon--active" size={48} />
                            <p className="dropzone__title">Drop files here!</p>
                        </>
                    ) : (
                        <>
                            <Upload className="dropzone__icon" size={48} />
                            <p className="dropzone__title">
                                Drag & drop files here, or click to browse
                            </p>
                            <p className="dropzone__subtitle">
                                Supports PDF, Images (PNG/JPG), and Excel (XLSX/XLS)
                            </p>
                        </>
                    )}
                </div>
            </div>

            {uploadedFiles.length > 0 && (
                <div className="uploaded-files">
                    <h4 className="uploaded-files__title">Processed Files</h4>
                    <ul className="uploaded-files__list">
                        {uploadedFiles.map((name, i) => (
                            <li key={i} className="uploaded-files__item">
                                <FileText size={16} />
                                <span>{name}</span>
                                <CheckCircle2 size={16} className="uploaded-files__check" />
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

export default FileUpload;
