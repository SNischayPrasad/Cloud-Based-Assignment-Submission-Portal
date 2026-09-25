import { useCallback, useEffect, useState } from 'react';
import { getErrorMessage } from '../services/api';

/**
 * Load data from the API when a page opens.
 *   const { data, error, loading, reload } = useLoad(() => service.get(id), [id]);
 */
export default function useLoad(loader, deps = []) {
  const [state, setState] = useState({ data: null, error: '', loading: true });

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(loader, deps);

  const reload = useCallback(() => {
    let active = true;
    setState((s) => ({ ...s, loading: true, error: '' }));
    run()
      .then((data) => active && setState({ data, error: '', loading: false }))
      .catch((err) => active && setState({ data: null, error: getErrorMessage(err), loading: false }));
    return () => {
      active = false;
    };
  }, [run]);

  useEffect(() => reload(), [reload]);

  return { ...state, reload, setData: (data) => setState((s) => ({ ...s, data })) };
}
