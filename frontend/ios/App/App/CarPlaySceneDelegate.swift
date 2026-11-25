import CarPlay
import MapKit
import UIKit

final class CarPlaySceneDelegate: UIResponder, CPTemplateApplicationSceneDelegate,
    CPPointOfInterestTemplateDelegate
{
    func templateApplicationScene(
        _ templateApplicationScene: CPTemplateApplicationScene,
        didConnect interfaceController: CPInterfaceController
    ) {
        let template = CPPointOfInterestTemplate(
            title: "Парковки рядом",
            pointsOfInterest: Self.parkings,
            selectedIndex: NSNotFound
        )
        template.pointOfInterestDelegate = self
        interfaceController.setRootTemplate(template, animated: false, completion: nil)
    }

    func pointOfInterestTemplate(
        _ pointOfInterestTemplate: CPPointOfInterestTemplate,
        didChangeMapRegion region: MKCoordinateRegion
    ) {
    }

    private static let parkings: [CPPointOfInterest] = [
        parking("Открытая стоянка", free: 9, latitude: 55.7690, longitude: 37.5940),
        parking("Двор жилого комплекса", free: 5, latitude: 55.7630, longitude: 37.6100),
        parking("Парковка бизнес-центра", free: 12, latitude: 55.7558, longitude: 37.6173),
    ]

    private static func parking(
        _ name: String,
        free: Int,
        latitude: CLLocationDegrees,
        longitude: CLLocationDegrees
    ) -> CPPointOfInterest {
        let coordinate = CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
        let mapItem = MKMapItem(placemark: MKPlacemark(coordinate: coordinate))
        mapItem.name = name
        return CPPointOfInterest(
            location: mapItem,
            title: name,
            subtitle: "Москва",
            summary: "Свободно мест: \(free)",
            detailTitle: name,
            detailSubtitle: "Москва",
            detailSummary: "Свободно мест: \(free)",
            pinImage: nil
        )
    }
}
