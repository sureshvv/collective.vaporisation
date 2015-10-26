# -*- coding: utf-8 -*-

from plone.app.contentlisting.interfaces import IContentListing
from plone.app.search.browser import Search as SearchView
from plone.app.search.browser import SortOption
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.interfaces import IPortletManager
from Products.CMFPlone.PloneBatch import Batch
from zope.component import getMultiAdapter
from zope.component import getUtilitiesFor
from zope.i18nmessageid import MessageFactory

_ = MessageFactory('plone')

import logging
logger = logging.getLogger('Plone')

class CloudSearch(SearchView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.types_list = ['Image']

    def findPortlet(self):
        portlet_path = self.request.form.get('path')
        portlet_name = self.request.form.get('portlet')
        portlet_context = self.context.restrictedTraverse(portlet_path)
        for manager_name, src_manager in getUtilitiesFor(IPortletManager, context=portlet_context):
            src_manager_assignments = getMultiAdapter((portlet_context, src_manager), IPortletAssignmentMapping)
            portlet_assignments = src_manager_assignments.get(portlet_name)
            if portlet_assignments:
                break
        return portlet_assignments

    def cloudQueryCatalog(self, use_types_blacklist=False, use_navigation_root=False,\
                          batch=True, b_size=7, b_start=0):
        results = []
        portlet_assignments = self.findPortlet()

        base_query = self.request.form.copy()
        if 'path' in base_query:
            del base_query['path']
        base_query['use_types_blacklist'] = use_types_blacklist
        base_query['use_navigation_root'] = use_navigation_root
        if portlet_assignments:
            # base_query['portal_type'] = portlet_assignments.type
            site_id = self.context.getId()
            base_query['path'] = '/' + site_id + (portlet_assignments.startpath or '')
        if batch:
            base_query['b_start'] = b_start = int(b_start)
            base_query['b_size'] = b_size
        tags = base_query.get('tags', None)
        logger.info('++SURESH PORTAL_TYPE: %s', base_query.get('portal_type', 'None'))
        if not tags:
            results = self.context.queryCatalog(base_query)
        else:
            for tag in tags:
                indexes = base_query.get(tag, [])
                result = []
                for index in indexes:
                    spec_query = base_query.copy()
                    spec_query[index] = {'query': tag,
                                         'operator': 'and'}
                    result.extend(self.context.queryCatalog(spec_query))
                if results:
                    results_uid = [brain.UID for brain in results]
                    results = [brain
                               for brain in result
                               if brain.UID in results_uid]
                else:
                    results = result
                results = self.clearResults(results)

        sort_key = base_query.get('sort_on', None)
        if sort_key == 'sortable_title':
            results.sort(key=lambda x: x.Title)
        elif sort_key == 'relevance':
            results.sort(key=lambda x: x.Description)
        else:
            results.sort(key=lambda x: x.effective, reverse=True)
        results = IContentListing(results)
        self.types_list = []
        for r in results:
            if r.portal_type not in self.types_list:
                self.types_list.append(r.portal_type)
        if batch:
            results = Batch(results, b_size, b_start)
        return results

    def types_list(self):
        return self.types_list

    def clearResults(self, results):
        uids = []
        unique_results = []
        for result in results:
            if result.UID not in uids:
                unique_results.append(result)
                uids.append(result.UID)
        return unique_results

    def get_tags(self):
        tags = self.request.get('tags', None)
        return ' for ' + ' plus '.join(tags) if tags else ''

    def sort_options(self):
        """ Sorting options for search results view. """
        return (
            MySortOption(self.request, _(u'date (newest first)'), '', reverse=True),
            MySortOption(self.request, _(u'alphabetically'), 'sortable_title'),
        )

class MySortOption(SortOption):
    def url(self):
        url = SortOption.url(self)
        if '@@updated_cloud_search' in url:
            url = url.replace('@@updated_cloud_search', '@@cloud_search')
        return url
