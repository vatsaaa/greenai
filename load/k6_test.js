import http from 'k6/http';
import { sleep } from 'k6';

export let options = {
  vus: 5,
  duration: '20s',
};

export default function () {
  http.get(__ENV.TARGET_URL || 'http://greenai-staging-bff:8000/health');
  sleep(1);
}
