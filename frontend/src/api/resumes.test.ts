// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { resumesApi } from './resumes';

class MockUploadRequest extends EventTarget {
  upload = new EventTarget();
  open = vi.fn();
  setRequestHeader = vi.fn();
  send = vi.fn();
  status = 0;
  responseText = '';
}

afterEach(() => vi.unstubAllGlobals());

describe('resume upload progress', () => {
  it('reports completed byte transfer as processing instead of capping it at 99%', () => {
    const request = new MockUploadRequest();
    vi.stubGlobal('XMLHttpRequest', class extends MockUploadRequest {
      constructor() {
        super();
        return request;
      }
    });
    const onProgress = vi.fn();

    void resumesApi.uploadResume(new File(['resume'], 'resume.pdf'), onProgress);
    const event = new Event('progress');
    Object.assign(event, { lengthComputable: true, loaded: 100, total: 100 });
    request.upload.dispatchEvent(event);

    expect(onProgress).toHaveBeenLastCalledWith(100, 'processing');
    expect(onProgress).not.toHaveBeenCalledWith(99, 'processing');
  });
});
